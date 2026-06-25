from urllib import request

from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer, UserSerializer as BaseUserSerializer
from rest_framework import serializers
from .models import CustomUser, Deposit, EdirChangeRequest, Family, Edir, FamilyChangeRequest, Fee, FeeAssignment, Bank, EdirUser, EdirUserChangeRequest, Help, Event, IncomeChangeRequest, Transaction, BankChangeRequest, ExpenseChangeRequest, FeeChangeRequest, TransactionChangeRequest
from django.db.models import Sum
from django.contrib.auth import password_validation

class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = CustomUser
        fields = ('id', 'phone_number', 'password', "re_password", 'full_name', 
                  "gender", "marital_status", "address")

    def validate_phone_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        return value

class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "phone_number"] # 

class VerySimpleEdirUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = EdirUser
        fields = ["id", "full_name", "phone_number"] # 

# Members
class SimpleEdirUserSerializer(serializers.ModelSerializer):
    requests = serializers.SerializerMethodField()
    class Meta:
        model = EdirUser
        fields = [
            'id',
            'full_name',
            'phone_number',
            'address',
            'status',
            'is_committee',
            'requests'
        ]
    def get_requests(self, obj):
        trx_request = TransactionChangeRequest.objects.filter(
            user=obj,
            status="PENDING"
        ).count()
        family_request = FamilyChangeRequest.objects.filter(
            edir_user=obj,
            status="PENDING"
        ).count()
        return trx_request + family_request


class UserWithRoleSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    is_committee = serializers.SerializerMethodField()
    membership_status = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'full_name',
            'phone_number',
            'address',
            'is_committee',
            'membership_status',
        ]  
    def get_edir_user(self, obj):
        edir = self.context.get("edir")
        if not edir:
            return None
        return obj.ediruser_set.filter(edir=edir).first()
        
    def get_full_name(self, obj):
        edir_user = self.get_edir_user(obj)
        return edir_user.full_name if edir_user else None

    def get_address(self, obj):
        edir_user = self.get_edir_user(obj)
        return edir_user.address if edir_user else None

    def get_is_committee(self, obj):
        edir_user = self.get_edir_user(obj)
        return edir_user.is_committee if edir_user else False
    
    def get_membership_status(self, obj):
        edir_user = self.get_edir_user(obj)
        if not edir_user:
            return "Not a Member"
        if edir_user.is_committee:
            return "Committee Member"
        return "Edir Member"

# Member detail
class EdirUserDetailSerializer(serializers.ModelSerializer):
    membership_status = serializers.SerializerMethodField()
    has_pending = serializers.SerializerMethodField()

    class Meta:
        model = EdirUser
        fields = [
            'id',
            'full_name',
            'phone_number',
            'gender',
            'marital_status',
            'profession',
            'address',
            'status',
            'is_committee',
            'membership_status',
            'has_pending',
        ]

    def get_membership_status(self, obj):
        if obj.edir is None:
            return "Not a Member"

        if obj.is_committee:
            return "Committee Member"

        return "Edir Member"
    
    def get_has_pending(self, obj):
        return EdirUserChangeRequest.objects.filter(
            edir_user=obj,
            status="PENDING"
        ).exists()


class EdirUserChangeRequestSerializer(serializers.ModelSerializer):
    maker = SimpleEdirUserSerializer(read_only=True)
    edir_user = EdirUserDetailSerializer(read_only=True)

    created_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S",
        read_only=True
    )

    class Meta:
        model = EdirUserChangeRequest
        fields = [
            "id",
            "edir_user",
            "action",
            "new_value",
            "old_value",
            "maker",
            'phone_number',
            "created_at",
        ]

class FamilyWithUserSerializer(serializers.ModelSerializer):
    has_edit_pending = serializers.SerializerMethodField()
    has_disable_pending = serializers.SerializerMethodField()
    class Meta:
        model = Family
        fields = [
            'id', 'full_name', 'gender', 'profession', 'relationship', 'user', 'has_edit_pending', 'has_disable_pending'
        ]
    
    def get_has_edit_pending(self, obj):
        return FamilyChangeRequest.objects.filter(
            family=obj,
            action="UPDATE",
            status="PENDING"
        ).exists()

    def get_has_disable_pending(self, obj):
        return FamilyChangeRequest.objects.filter(
            family=obj,
            action="DISABLE",
            status="PENDING"
        ).exists()

class FamilyChangeRequestSerializer(serializers.ModelSerializer):
    maker = SimpleEdirUserSerializer(read_only=True)
    family = FamilyWithUserSerializer(read_only=True)

    created_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S",
        read_only=True
    )

    class Meta:
        model = FamilyChangeRequest
        fields = [
            "id",
            "family",
            "action",
            "new_value",
            "old_value",
            "maker",
            "created_at",
        ]


class EdirSerializer(serializers.ModelSerializer):
    meeting_date = serializers.DateField(
        input_formats=["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"],
        required=False,
        allow_null=True,
    )
    class Meta:
        model = Edir
        fields = [ 
            "is_popular", 
            "status", 
            "id",
            "name",
            "monthly_fee",
            "address",
            "description",
            "meeting_date",
            "meeting_place",
        ] 
        read_only_fields = (
            "is_popular",
            "status",
        )

class EdirDetailSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Edir
        fields = [
            "id", "name", "monthly_fee", "address", "description", 
            "meeting_date", "meeting_place", "member_count"
        ]
    def get_member_count(self, obj):
        return EdirUser.objects.filter(edir=obj, status="Active").count()    
    
# Dashboard
class EdirDetailOnDashboardSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    unpaid_fees_total_amount = serializers.SerializerMethodField()
    unpaid_fees_total = serializers.SerializerMethodField()
    committee_members = serializers.SerializerMethodField()

    class Meta:
        model = Edir
        fields = [
            "id", "name", "monthly_fee", "meeting_date", "meeting_place",
            "member_count", "unpaid_fees_total_amount","unpaid_fees_total", "committee_members"
        ]
    def get_member_count(self, obj):
        return EdirUser.objects.filter(edir=obj, status="Active").count()
    def get_unpaid_fees_total_amount(self, obj):
        user = self.context.get("request").user
        current_user = EdirUser.objects.filter(
            user=user,
            edir=obj,
            status="Active"
        ).only("id").first()
        total = (
            FeeAssignment.objects.filter(
                user=current_user,
                fee__edir=obj,
                transaction=None,  
            )
            .aggregate(total=Sum("fee__amount"))["total"]
        )
        return total or 0
    def get_unpaid_fees_total(self, obj):
        user = self.context.get("request").user
        current_user = EdirUser.objects.filter(
            user=user,
            edir=obj,
            status="Active"
        ).only("id").first()
        total = FeeAssignment.objects.filter(
                user=current_user,
                fee__edir=obj,
                transaction=None,  
            ).count()
        return total or 0
    def get_committee_members(self, obj):
        committees = EdirUser.objects.filter(
            edir=obj,
            is_committee=True,
            status="Active"
        )
        return SimpleEdirUserSerializer(committees, many=True).data
        
class EdirChangeRequestSerializer(serializers.ModelSerializer):
    maker = SimpleEdirUserSerializer(read_only=True)
    edir = EdirSerializer(read_only=True)

    created_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S",
        read_only=True
    )

    class Meta:
        model = EdirChangeRequest
        fields = [
            "id",
            "edir",
            "action",
            "new_value",
            "old_value",
            "maker",
            "created_at",
        ]

class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = [
            'id', 'bank_name', 'account_number', 'account_name','status', 'amount', 
        ]

class BankChangeRequestSerializer(serializers.ModelSerializer):
    maker = SimpleEdirUserSerializer(read_only=True)
    bank = BankSerializer(read_only=True)

    created_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S",
        read_only=True
    )

    class Meta:
        model = BankChangeRequest
        fields = [
            "id",
            "bank",
            "action",
            "new_value",
            "old_value",
            "maker",
            "created_at",
        ]


class BankWithEdirSerializer(serializers.ModelSerializer):
    has_pending = serializers.SerializerMethodField()
    class Meta:
        model = Bank
        fields = [
            'id', 
            'bank_name', 
            'account_number', 
            'account_name',
            'amount',
            'status', 
            'edir', 
            'has_pending',
        ]

    def get_has_pending(self, obj):
        return BankChangeRequest.objects.filter(
            bank=obj,
            status="PENDING"
        ).exists()
    
class FeeSerializer(serializers.ModelSerializer):
    supported_member = SimpleEdirUserSerializer(read_only=True)

    class Meta:
        model = Fee
        fields = "__all__"
        
class FeeDetailSerializer(serializers.ModelSerializer):
    supported_member = SimpleEdirUserSerializer(read_only=True)
    assigned_users = serializers.SerializerMethodField()
    has_pending = serializers.SerializerMethodField()

    class Meta:
        model = Fee
        fields = [
            "id",
            "name",
            "category",
            "amount",
            "reason",
            "supported_member",
            "payment_date",
            "created_date",
            "status",
            "assigned_users",
            "has_pending",
        ]
    def get_assigned_users(self, obj):
        assignments = obj.feeassignment_fee.select_related(
            "user",
            "transaction"
        ).all()

        result = []

        for a in assignments:
            result.append({
                "id": a.user.id if a.user else None,
                "full_name": a.user.full_name if a.user else None,
                "payment_status": (
                    a.transaction.payment_status
                    if a.transaction else None
                ),
                "transaction_request_status": (
                    a.transaction_change_request.status
                    if a.transaction_change_request
                    else None
                )
            })

        return result
    def get_has_pending(self, obj):
        return FeeChangeRequest.objects.filter(
            fee=obj,
            # action="UPDATE",
            status="PENDING"
        ).exists()
    

class FeeChangeRequestSerializer(serializers.ModelSerializer):
    maker = SimpleEdirUserSerializer(read_only=True)
    fee = FeeDetailSerializer(read_only=True)

    created_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S",
        read_only=True
    )

    class Meta:
        model = FeeChangeRequest
        fields = [
            "id",
            "fee",
            "action",
            "new_value",
            "old_value",
            "maker",
            "created_at",
        ]
    def to_representation(self, instance):
        data = super().to_representation(instance)

        new_value = data.get("new_value")
        old_value = data.get("old_value")
        if new_value and new_value.get("supported_member"):
            user_id = new_value["supported_member"]

            try:
                user = EdirUser.objects.get(id=user_id)
                new_value["supported_member"] = {
                    "id": user.id,
                    "full_name": user.full_name
                }
            except EdirUser.DoesNotExist:
                pass
        if old_value and old_value.get("supported_member"):
            user_id = old_value["supported_member"]

            try:
                user = EdirUser.objects.get(id=user_id)
                old_value["supported_member"] = {
                    "id": user.id,
                    "full_name": user.full_name
                }
            except EdirUser.DoesNotExist:
                pass

        if new_value and new_value.get("users"):
            user_ids = new_value["users"]

            users = EdirUser.objects.filter(id__in=user_ids)
            new_value["users"] = [
                {
                    "id": user.id,
                    "full_name": user.full_name
                }
                for user in users
            ]

        if old_value and old_value.get("users"):
            user_ids = old_value["users"]

            users = EdirUser.objects.filter(id__in=user_ids)
            old_value["users"] = [
                {
                    "id": user.id,
                    "full_name": user.full_name
                }
                for user in users
            ]

        return data

class ExpenseDetailSerializer(serializers.ModelSerializer):
    supported_member = SimpleEdirUserSerializer(read_only=True)
    has_pending = serializers.SerializerMethodField()
    
    payment_method = serializers.SerializerMethodField()
    bank_id = serializers.SerializerMethodField()
    bank_name = serializers.SerializerMethodField()

    class Meta:
        model = Fee
        fields = [
            "id",
            "name",
            "category",
            "amount",
            "reason",
            "supported_member",
            "payment_date",
            "created_date",
            "status",
            "has_pending",
            "payment_method",
            "bank_id",
            "bank_name",
        ]
    def get_has_pending(self, obj):
        return ExpenseChangeRequest.objects.filter(
            fee=obj,
            status="PENDING"
        ).exists()

    def get_payment_method(self, obj):
        fee_assignment = obj.feeassignment_fee.select_related(
            "transaction"
        ).first()

        if fee_assignment and fee_assignment.transaction:
            return fee_assignment.transaction.payment_method

        return None

    def get_bank_name(self, obj):
        fee_assignment = obj.feeassignment_fee.select_related(
            "transaction__deposit__bank"
        ).first()

        if (
            fee_assignment
            and fee_assignment.transaction
            and fee_assignment.transaction.deposit
            and fee_assignment.transaction.deposit.bank
        ):
            return fee_assignment.transaction.deposit.bank.bank_name

        return None

    def get_bank_id(self, obj):
        fee_assignment = obj.feeassignment_fee.select_related(
            "transaction__deposit__bank"
        ).first()

        if (
            fee_assignment
            and fee_assignment.transaction
            and fee_assignment.transaction.deposit
            and fee_assignment.transaction.deposit.bank
        ):
            return fee_assignment.transaction.deposit.bank.id

        return None

class ExpenseChangeRequestSerializer(serializers.ModelSerializer):
    maker = SimpleEdirUserSerializer(read_only=True)
    fee = ExpenseDetailSerializer(read_only=True)
    bank = BankSerializer(read_only=True)

    created_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S",
        read_only=True
    )

    class Meta:
        model = ExpenseChangeRequest
        fields = [
            "id",
            "fee",
            "action",
            "new_value",
            "old_value",
            "maker",
            "bank",
            "created_at",
        ]
    def to_representation(self, instance):
        data = super().to_representation(instance)

        new_value = data.get("new_value")
        old_value = data.get("old_value")
        
        if new_value:
            bank_id = new_value.get("bank")
            if bank_id and str(bank_id).isdigit():  
                bank = Bank.objects.filter(id=int(bank_id)).first()
                if bank:
                    new_value["bank"] = {
                        "id": bank.id,
                        "name": bank.bank_name
                    }
                else:
                    new_value["bank"] = None
            else:
                new_value["bank"] = None
        if new_value and new_value.get("supported_member"):
            user_id = new_value["supported_member"]

            try:
                user = EdirUser.objects.get(id=user_id)
                new_value["supported_member"] = {
                    "id": user.id,
                    "full_name": user.full_name
                }
            except EdirUser.DoesNotExist:
                pass
        
        if old_value:
            bank_id = old_value.get("bank")
            if bank_id and str(bank_id).isdigit():  
                bank = Bank.objects.filter(id=int(bank_id)).first()
                if bank:
                    old_value["bank"] = {
                        "id": bank.id,
                        "name": bank.bank_name
                    }
                else:
                    old_value["bank"] = None
            else:
                old_value["bank"] = None

        if old_value and old_value.get("supported_member"):
            user_id = old_value["supported_member"]["id"] if isinstance(old_value["supported_member"], dict) else old_value["supported_member"]

            try:
                user = EdirUser.objects.get(id=user_id)
                old_value["supported_member"] = {
                    "id": user.id,
                    "full_name": user.full_name
                }
            except EdirUser.DoesNotExist:
                pass

        return data


class IncomeDetailSerializer(serializers.ModelSerializer):
    supported_member = SimpleEdirUserSerializer(read_only=True)
    has_pending = serializers.SerializerMethodField()

    payment_method = serializers.SerializerMethodField()
    bank_id = serializers.SerializerMethodField()
    bank_name = serializers.SerializerMethodField()

    class Meta:
        model = Fee
        fields = [
            "id",
            "name",
            "category",
            "amount",
            "reason",
            "supported_member",
            "payment_date",
            "created_date",
            "status",
            "has_pending",
            "payment_method",
            "bank_id",
            "bank_name",
        ]
    def get_has_pending(self, obj):
        return IncomeChangeRequest.objects.filter(
            fee=obj,
            status="PENDING"
        ).exists()

    def get_payment_method(self, obj):
        fee_assignment = obj.feeassignment_fee.select_related(
            "transaction"
        ).first()

        if fee_assignment and fee_assignment.transaction:
            return fee_assignment.transaction.payment_method

        return None

    def get_bank_name(self, obj):
        fee_assignment = obj.feeassignment_fee.select_related(
            "transaction__deposit__bank"
        ).first()

        if (
            fee_assignment
            and fee_assignment.transaction
            and fee_assignment.transaction.deposit
            and fee_assignment.transaction.deposit.bank
        ):
            return fee_assignment.transaction.deposit.bank.bank_name

        return None

    def get_bank_id(self, obj):
        fee_assignment = obj.feeassignment_fee.select_related(
            "transaction__deposit__bank"
        ).first()

        if (
            fee_assignment
            and fee_assignment.transaction
            and fee_assignment.transaction.deposit
            and fee_assignment.transaction.deposit.bank
        ):
            return fee_assignment.transaction.deposit.bank.id

        return None

class PaymentChangeRequestSerializer(serializers.ModelSerializer):
    maker = SimpleEdirUserSerializer(read_only=True)
    user = SimpleEdirUserSerializer(read_only=True)

    created_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S",
        read_only=True
    )

    class Meta:
        model = TransactionChangeRequest
        fields = [
            "id",
            "trx",
            "action",
            "new_value",
            "old_value",
            "maker",
            "user",
            "created_at",
            "image",
        ]
        
    def to_representation(self, instance):
        data = super().to_representation(instance)

        new_value = data.get("new_value")
        old_value = data.get("old_value")
        request = self.context.get('request')
        if  instance.image:
            data['image'] = request.build_absolute_uri(instance.image.url) if request else instance.image.url
        else:
            data['image'] = None

        if new_value:
            bank_id = new_value.get("bank")

            if bank_id and str(bank_id).isdigit():  # ✅ important validation
                bank = Bank.objects.filter(id=int(bank_id)).first()
                if bank:
                    new_value["bank"] = {
                        "id": bank.id,
                        "name": bank.bank_name
                    }
                else:
                    new_value["bank"] = None
            else:
                new_value["bank"] = None

        if new_value and new_value.get("fees"):
            fee_ids = new_value["fees"]
            fees_list = []

            for fee_id in fee_ids:
                try:
                    fee = Fee.objects.get(id=fee_id)

                    supported_member = None
                    if fee.supported_member:
                        user = EdirUser.objects.get(id=fee.supported_member.id)
                        supported_member = {
                            "id": user.id,
                            "full_name": user.full_name
                        }

                    fees_list.append({
                        "id": fee.id,
                        "fee_name": fee.name,
                        "amount": fee.amount,
                        "category": fee.category,
                        "supported_member": supported_member
                    })

                except (EdirUser.DoesNotExist, Fee.DoesNotExist):
                    pass

            new_value["fees"] = fees_list  
        
        if old_value:
            bank_id = old_value.get("bank")

            if bank_id and str(bank_id).isdigit():  # ✅ important validation
                bank = Bank.objects.filter(id=int(bank_id)).first()
                if bank:
                    old_value["bank"] = {
                        "id": bank.id,
                        "name": bank.bank_name
                    }
                else:
                    old_value["bank"] = None
            else:
                old_value["bank"] = None

        if old_value and old_value.get("fees"):
            fee_ids = old_value["fees"]   # ❗ FIX (you used new_value before)
            fees_list = []

            for fee_id in fee_ids:
                try:
                    fee = Fee.objects.get(id=fee_id)

                    supported_member = None
                    if fee.supported_member:
                        user = EdirUser.objects.get(id=fee.supported_member.id)
                        supported_member = {
                            "id": user.id,
                            "full_name": user.full_name
                        }

                    fees_list.append({
                        "id": fee.id,
                        "fee_name": fee.name,
                        "amount": fee.amount,
                        "category": fee.category,
                        "supported_member": supported_member
                    })

                except (EdirUser.DoesNotExist, Fee.DoesNotExist):
                    pass

            old_value["fees"] = fees_list  # ✅ correct target

        return data

class FeeAssignmentSerializer(serializers.ModelSerializer):
    fee_id = serializers.IntegerField(source="fee.id")
    name = serializers.CharField(source="fee.name")
    amount = serializers.IntegerField(source="fee.amount") #, max_digits=10, decimal_places=2
    category = serializers.CharField(source="fee.category")
    supported_member = serializers.SerializerMethodField()

    assignment_id = serializers.IntegerField(source="id")
    class Meta:
        model = FeeAssignment
        fields = [
            "assignment_id",
            "fee_id",
            "name",
            "amount",
            "category",
            "supported_member",
        ]

    def get_supported_member(self, obj):
        return obj.fee.supported_member.full_name if obj.fee.supported_member else None
    

class DepositForTransactionSerializer(serializers.ModelSerializer):
    bank = BankSerializer(read_only=True)

    class Meta:
        model = Deposit
        fields = [
            "id",
            "bank",
            "image",
        ]
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if  instance.image:
            data['image'] = request.build_absolute_uri(instance.image.url) if request else instance.image.url
        else:
            data['image'] = None
        return data


# Payment Details
class TransactionSerializer(serializers.ModelSerializer):
    deposit = DepositForTransactionSerializer(read_only=True)  
    fees = FeeAssignmentSerializer(source="feeassignment_trx", many=True)
    maker = serializers.SerializerMethodField()
    has_pending = serializers.SerializerMethodField()

    total_amount = serializers.IntegerField(source="amount")
    class Meta:
        model = Transaction
        fields = [
            "reference",
            "created_at",
            "payment_method",
            "transaction_type",
            "total_amount",
            "payment_status",
            "fees",
            "has_pending",
            "maker",
            "deposit"
        ]

    def get_has_pending(self, obj):
        return TransactionChangeRequest.objects.filter(
            prev_trx=obj,
            status="PENDING"
        ).exists()

    def get_maker(self, obj):
        maker =  (
            TransactionChangeRequest.objects
            .filter(trx=obj)
            .select_related("maker")
            .values("maker__id", "maker__full_name")
            .first()
        )
        if maker:
            return {
                "id": maker["maker__id"],
                "full_name": maker["maker__full_name"],
            }

        return None

class SimpleDepositSerializer(serializers.ModelSerializer):
    bank = BankSerializer(read_only=True)
    user = SimpleEdirUserSerializer(read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Deposit
        fields = [
            "id",
            "bank",
            "created_at",
            "transaction_type",
            "payment_method",
            "user",
            "total_amount",
        ]

class UndepositedTransactionSerializer(serializers.ModelSerializer):
    user = VerySimpleEdirUserSerializer(read_only=True)
    payment_date = serializers.DateTimeField(
        source="created_at"
    )
    fees = FeeAssignmentSerializer(
        source="feeassignment_trx",
        many=True,
        read_only=True
    )

    class Meta:
        model = Transaction
        fields = [
            "id",
            "amount",
            "user",
            "payment_date",
            "payment_method",
            "fees",
        ]

# Dashboard
class PaymentSerializer(serializers.ModelSerializer):
    fees = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            "reference",
            "amount",
            "payment_method",
            "created_at",
            "transaction_type",
            "payment_status",
            "fees",
        ]

    def get_fees(self, obj):
        fees = []

        for assignment in obj.feeassignment_trx.all():
            fee = assignment.fee

            if fee:
                fees.append({
                    "id": fee.id,
                    "name": fee.name,
                    "category": fee.category,
                    "amount": fee.amount,
                    "supported_member": (
                        fee.supported_member.full_name
                        if fee.supported_member
                        else None
                    ),
                })

        return fees

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)


    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is not correct')
        return value

    def validate(self, data):
        new = data.get('new_password')
        confirm = data.get('confirm_password')
        if new != confirm:
            raise serializers.ValidationError({'confirm_password': 'Password confirmation does not match'})
        
        try:
            password_validation.validate_password(new, self.context['request'].user)
        except Exception as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
        return data
    
# Dashboard
class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"

class HelpSerializer(serializers.ModelSerializer):
    class Meta:
        model = Help
        fields = ["id", "question", "answer", "type"]
