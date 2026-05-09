from urllib import request

from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer, UserSerializer as BaseUserSerializer
from rest_framework import serializers
from .models import CustomUser, Deposit, EdirChangeRequest, Family, Edir, FamilyChangeRequest, Fee, FeeAssignment, Bank, EdirUser, EdirUserChangeRequest, Help, Event, Transaction, BankChangeRequest, ExpenseChangeRequest, FeeChangeRequest, TransactionChangeRequest
import calendar
from datetime import date
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
    

class EdirSerializer(serializers.ModelSerializer):
    meeting_date = serializers.DateField(
        input_formats=["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"],
        required=False,
        allow_null=True,
    )
    class Meta:
        model = Edir
        fields = [ 
            # "created_by", 
            "is_popular", 
            "status", 
            "updated_date",
            "id",
            "name",
            "monthly_fee",
            "address",
            "description",
            "created_date",
            "meeting_date",
            "meeting_place",
        ] 
        read_only_fields = (
            # "created_by",
            "created_date",
            "updated_date",
            "is_popular",
            "status",
        )


class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "phone_number"] # 

class SimpleEdirUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = EdirUser
        fields = ["id", "full_name", "phone_number"] # 

class UserWithRoleSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    # gender = serializers.SerializerMethodField()
    # marital_status = serializers.SerializerMethodField()
    # profession = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    is_committee = serializers.SerializerMethodField()
    membership_status = serializers.SerializerMethodField()
    # number_of_family = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'full_name',
            'phone_number',
            # 'gender',
            # 'marital_status',
            # 'profession',
            'address',
            # 'number_of_family',
            'is_committee',
            'membership_status',
        ]
    # def get_edir_user(self, obj):
    #     edir = self.context.get("edir")

    #     try:
    #         return obj.ediruser_set.get(edir=edir)
    #     except EdirUser.DoesNotExist:
    #         return None
        
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

class EdirUserWithNumFamSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    edir = EdirSerializer(read_only=True)
    membership_status = serializers.SerializerMethodField()
    
    has_edit_pending = serializers.SerializerMethodField()
    has_disable_pending = serializers.SerializerMethodField()

    class Meta:
        model = EdirUser
        fields = [
            'id',
            'edir',
            'user_id',
            'full_name',
            'phone_number',
            'gender',
            'marital_status',
            'profession',
            'address',
            'status',
            'is_committee',
            'membership_status',
            'has_edit_pending',
            'has_disable_pending'

        ]

    def get_membership_status(self, obj):
        if obj.edir is None:
            return "Not a Member"

        if obj.is_committee:
            return "Committee Member"

        return "Edir Member"
    
    def get_has_edit_pending(self, obj):
        return EdirUserChangeRequest.objects.filter(
            edir_user=obj,
            action="UPDATE",
            status="PENDING"
        ).exists()

    def get_has_disable_pending(self, obj):
        return EdirUserChangeRequest.objects.filter(
            edir_user=obj,
            action="DISABLE",
            status="PENDING"
        ).exists()


class EdirUserDetailSerializer(serializers.ModelSerializer):
    membership_status = serializers.SerializerMethodField()
    
    has_edit_pending = serializers.SerializerMethodField()
    has_disable_pending = serializers.SerializerMethodField()

    class Meta:
        model = EdirUser
        fields = [
            'id',
            'edir',
            'user',
            'full_name',
            'phone_number',
            'gender',
            'marital_status',
            'profession',
            'address',
            'status',
            'is_committee',
            'membership_status',
            'has_edit_pending',
            'has_disable_pending'
        ]

    def get_membership_status(self, obj):
        if obj.edir is None:
            return "Not a Member"

        if obj.is_committee:
            return "Committee Member"

        return "Edir Member"
    
    def get_has_edit_pending(self, obj):
        return EdirUserChangeRequest.objects.filter(
            edir_user=obj,
            action="UPDATE",
            status="PENDING"
        ).exists()

    def get_has_disable_pending(self, obj):
        return EdirUserChangeRequest.objects.filter(
            edir_user=obj,
            action="DISABLE",
            status="PENDING"
        ).exists()


class UserWithNumFam2Serializer(serializers.ModelSerializer):
    id = serializers.CharField(source="user.id")
    full_name = serializers.CharField(source="user.full_name")
    phone_number = serializers.CharField(source="user.phone_number")
    gender = serializers.CharField(source="user.gender")
    marital_status = serializers.CharField(source="user.marital_status")
    profession = serializers.CharField(source="user.profession")
    # city = serializers.CharField(source="user.city")
    address = serializers.CharField(source="user.address")
    user_status = serializers.CharField(source="status")
    # is_committee = serializers.CharField(source="is_committee")
    number_of_family = serializers.SerializerMethodField()

    class Meta:
        model = EdirUser 
        fields = [
            'id', 'full_name', 'phone_number',  'gender', 'marital_status', 
            'profession', 'address', "user_status", "number_of_family", "is_committee"
        ]
    def get_number_of_family(self, obj):
        return obj.user.family.filter(status="Active").count()
        

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

# class AddEdirSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Edir
#         fields = [
#             "id", "name", "monthly_fee", "address", "description",
#             "created_date", "meeting_date", "meeting_place",
#         ]
#         read_only_fields = ["id", "created_date", ]
class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = [
            'id', 'bank_name', 'account_number', 'account_name','status', 'amount', 
        ]

        
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


class EdirWithUsersSerializer(serializers.ModelSerializer):
    users = serializers.PrimaryKeyRelatedField(read_only=True, many=True)

    class Meta:
        model = Edir
        fields = [
            "id",
            "name",
            "monthly_fee",
            "address",
            "description",
            "created_date",
            "users",  
        ]
        read_only_fields = ["id", "created_date", "users"]


class BankWithEdirSerializer(serializers.ModelSerializer):
    has_edit_pending = serializers.SerializerMethodField()
    has_disable_pending = serializers.SerializerMethodField()
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
            'has_edit_pending',
            'has_disable_pending',
        ]
    
    def get_has_edit_pending(self, obj):
        return BankChangeRequest.objects.filter(
            bank=obj,
            action="UPDATE",
            status="PENDING"
        ).exists()

    def get_has_disable_pending(self, obj):
        return BankChangeRequest.objects.filter(
            bank=obj,
            action="DISABLE",
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


# class PaymentSerializer(serializers.ModelSerializer):
#     user_name = serializers.CharField(source="user.username", read_only=True)
#     edir_name = serializers.CharField(source="edir.name", read_only=True)

#     class Meta:
#         model = Payment
#         fields = ["id", "user", "user_name", "edir", "edir_name", "month", "amount", "payment_date"]

class UserWithEdirsSerializer(serializers.ModelSerializer):
    edirs = EdirSerializer(many=True, read_only=True)

    class Meta:
        model = CustomUser
        fields = ["id", "full_name", "phone_number", "edirs"]
        read_only_fields = ["id", "edirs"]

# class PaymentSerializer(serializers.ModelSerializer):

#     class Meta:
#         model = Payment
#         fields = "__all__"

# class BillSerializer(serializers.ModelSerializer):
#     bill = PaymentSerializer(read_only=True)
#     class Meta:
#         model = Bill
#         fields = "__all__"

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"

# class SemiBillSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Bill
#         fields = ["id", "month", "amount"]

class HelpSerializer(serializers.ModelSerializer):
    class Meta:
        model = Help
        fields = ["id", "question", "answer", "type"]

# class PaymentDetailsSerializer(serializers.ModelSerializer):
#     bills = SemiBillSerializer(source="payment", many=True)  # related_name="payment" from Bill model
#     total_amount = serializers.SerializerMethodField()

#     class Meta:
#         model = Payment
#         fields = ["id", "method", "paid_at", "bills", "total_amount"]

#     def get_total_amount(self, obj):
#         return sum(bill.amount for bill in obj.payment.all())
    
class EdirWithUserStatusSerializer(serializers.ModelSerializer):
    user_status = serializers.SerializerMethodField()

    class Meta:
        model = Edir
        fields = "__all__"   # or list your fields
        extra_fields = ["user_status"]

    def get_user_status(self, obj):
        request = self.context.get("request")
        if not request:
            return None

        edir_user = obj.ediruser_set.filter(user=request.user).first()
        return edir_user.status if edir_user else None

    
# class EdirDetailSerializer1(serializers.ModelSerializer):
#     member_count = serializers.SerializerMethodField()
#     committee_members = serializers.SerializerMethodField()

#     class Meta:
#         model = Edir
#         fields = [
#             "id",
#             "name",
#             "monthly_fee",
#             "address",
#             "description",
#             "created_date",
#             "member_count",
#             "committee_members"
#         ]

#     def get_member_count(self, obj):
#         return EdirUser.objects.filter(edir=obj, status="Active").count()

#     def get_committee_members(self, obj):
#         committee_users = EdirUser.objects.filter(edir=obj, is_committee=True)
#         return [user.user.full_name for user in committee_users]

    
class EdirDetailSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    unpaid_fees_total = serializers.SerializerMethodField()
    committee_members = serializers.SerializerMethodField()

    class Meta:
        model = Edir
        fields = [
            "id", "name", "monthly_fee", "address", "description", "meeting_date", "meeting_place",
            "created_date", "member_count", "unpaid_fees_total", "committee_members"
        ]
    def get_member_count(self, obj):
        return EdirUser.objects.filter(edir=obj, status="Active").count()
    def get_unpaid_fees_total(self, obj):
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
                fee__fee_type="Income",
            )
            .exclude(transaction__payment_status="Paid")
            .aggregate(total=Sum("fee__amount"))["total"]
        )
        return total or 0
    def get_committee_members(self, obj):
        committees = EdirUser.objects.filter(
            edir=obj,
            is_committee=True,
            status="Active"
        )
        # .select_related("user")

        # members = [link.user for link in committee_links]
        return EdirUserWithNumFamSerializer(committees, many=True).data
    

class EdirDetailHeaderSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Edir
        fields = [
            "id", "name", "monthly_fee", "address", "description", "meeting_date", "meeting_place",
            "created_date", "member_count", 
        ]
    def get_member_count(self, obj):
        return EdirUser.objects.filter(edir=obj, status="Active").count()


# class BillSummarySerializer(serializers.Serializer):
#     # edir_id = serializers.IntegerField()
#     payment_date = serializers.DateField()
#     total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class FeeAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeAssignment
        fields = "__all__"

class FeeSerializer(serializers.ModelSerializer):
    supported_member = SimpleUserSerializer(read_only=True)

    class Meta:
        model = Fee
        fields = "__all__"

class TransactionSerializer(serializers.Serializer):
    Trx_ref = serializers.CharField()
    paid_date = serializers.DateTimeField()
    method = serializers.CharField()
    total_amount = serializers.IntegerField()#max_digits=10, decimal_places=2
    fees = serializers.SerializerMethodField()

#     def get_fees(self, obj):
#         fees = FeeAssignment.objects.filter(Trx_ref=obj["Trx_ref"]).select_related("fee")
#         return FeeSerializer([f.fee for f in fees], many=True).data

# class FeeAssignmentReadOnlySerializer(serializers.ModelSerializer):
#     fee_id = serializers.IntegerField(source="fee.id", read_only=True)
#     # fee_name = serializers.CharField(source="fee.name", read_only=True)
#     fee_amount = serializers.DecimalField(source="fee.amount", max_digits=10, decimal_places=2, read_only=True)
#     fee_category = serializers.CharField(source="fee.category", read_only=True)

#     class Meta:
#         model = FeeAssignment
#         fields = ["fee_id", "fee_amount", "fee_category", "status", "created_date"]

class TransactionsSerializer(serializers.ModelSerializer):
    user = SimpleEdirUserSerializer(read_only=True)
    class Meta:
        model = Transaction
        fields = ["id", "reference", "amount", "user", "payment_method","payment_status", "created_at"]

class DepositSerializer(serializers.ModelSerializer):
    transactions = TransactionsSerializer(many=True, read_only=True)
    bank = BankSerializer(read_only=True)
    user = SimpleEdirUserSerializer(read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Deposit
        fields = [
            "id",
            "bank",
            "created_at",
            "transactions",
            "payment_method",
            "user",
            "total_amount",
        ]

class SupportedMemberSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()


class FeeAssignmentReadOnlySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    fee_id = serializers.IntegerField(source="fee.id", read_only=True)
    fee_name = serializers.CharField(source="fee.name", read_only=True)
    category = serializers.CharField(source="fee.category", read_only=True)
    amount = serializers.IntegerField(
        source="fee.amount",
        read_only=True
    ) # max_digits=10, decimal_places=2,
    payment_date = serializers.DateField(source="fee.payment_date", read_only=True)
    # payment_method = serializers.CharField(source="transaction.payment_method", read_only=True)

    supported_member = serializers.SerializerMethodField()

    class Meta:
        model = FeeAssignment
        fields = [
            "id",
            "fee_id",
            "fee_name",
            "category",
            "amount",
            "supported_member",
            "payment_date",
            # "payment_method",
        ]

    def get_supported_member(self, obj):
        member = obj.fee.supported_member
        if member:
            return {
                "id": member.id,
                "full_name": member.full_name,
            }
        return None

# class WithdrawalSerializer(serializers.ModelSerializer):
#     # fee_name = serializers.CharField(source="fee.name", read_only=True)
#     fee_amount = serializers.DecimalField(source="fee.amount", max_digits=10, decimal_places=2, read_only=True)
#     user_full_name = serializers.CharField(source="user.full_name", read_only=True)
#     # trx_transaction_type = serializers.CharField(source="trx.transaction_type", read_only=True)
#     # trx_payment_method = serializers.CharField(source="trx.payment_method", read_only=True)
#     # trx_payment_status = serializers.CharField(source="trx.payment_status", read_only=True)
#     class Meta:
#         model = FeeAssignment
#         fields = ["id", "fee_amount", "user_full_name"]

# class FeeAssignmentDetailSerializer(serializers.ModelSerializer):
#     user_full_name = serializers.CharField(source="fee.supported_member.full_name", read_only=True)
#     fee_name = serializers.CharField(source="fee.name", read_only=True)
#     fee_amount = serializers.DecimalField(source="fee.amount", max_digits=10, decimal_places=2, read_only=True)
#     fee_category = serializers.CharField(source="fee.category", read_only=True)
#     fee_reason = serializers.CharField(source="fee.reason", read_only=True)
#     payment_date = serializers.CharField(source="fee.created_date", read_only=True)

#     class Meta:
#         model = FeeAssignment
#         fields = [
#             "id",
#             # "fee_name",
#             "fee_amount",
#             "fee_category",
#             "fee_reason",
#             # "transaction_type",
#             "payment_status",
#             # "payment_method",
#             "payment_date",
#             # "Trx_ref",
#             "user_full_name",
#         ]
    # def to_representation(self, instance):
    #     data = super().to_representation(instance)
    #     if not data.get("user_full_name"):
    #         data["user_full_name"] = "Edir"

    #     return data
class FeeAssignmentDetailSerializer(serializers.ModelSerializer):

    user_full_name = serializers.SerializerMethodField()
    fee_name = serializers.SerializerMethodField()
    fee_amount = serializers.IntegerField(
        source="fee.amount",
        read_only=True
    ) # max_digits=10, decimal_places=2,
    fee_category = serializers.CharField(source="fee.category", read_only=True)
    fee_reason = serializers.CharField(source="fee.reason", read_only=True)

    payment_status = serializers.SerializerMethodField()
    payment_date = serializers.SerializerMethodField()

    class Meta:
        model = FeeAssignment
        fields = [
            "id",
            "fee_name",
            "fee_amount",
            "fee_category",
            "fee_reason",
            "payment_status",
            "payment_date",
            "user_full_name",
        ]

    # ✅ supported_member safe access
    def get_user_full_name(self, obj):
        if obj.fee and obj.fee.supported_member:
            return obj.fee.supported_member.full_name
        return None

    def get_fee_name(self, obj):
        if obj.fee:
            return obj.fee.name or ""
        return ""

    # ✅ transaction may not exist
    def get_payment_status(self, obj):
        if hasattr(obj, "transaction") and obj.transaction:
            return obj.transaction.payment_status
        return "PENDING"

    def get_payment_date(self, obj):
        if hasattr(obj, "transaction") and obj.transaction:
            return obj.transaction.approved_at
        return None
    
class FeeTrxSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)
    trx_payment_method = serializers.CharField(source="trx.payment_method", read_only=True)
    trx_ref = serializers.CharField(source="trx.reference", read_only=True)
    trx_payment_status = serializers.CharField(source="trx.payment_status", read_only=True)
    trx_type = serializers.CharField(source="trx.transaction_type", read_only=True)

    class Meta:
        model = FeeAssignment
        fields = ["id", "user_full_name", "trx_payment_method", "trx_ref", "trx_type", "payment_status", "payment_date"]
        
class FeeDetailSerializer(serializers.ModelSerializer):
    supported_member = SimpleEdirUserSerializer(read_only=True)
    has_edit_pending = serializers.SerializerMethodField()
    has_disable_pending = serializers.SerializerMethodField()

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
            "has_edit_pending",
            "has_disable_pending",
        ]
    def get_has_edit_pending(self, obj):
        return FeeChangeRequest.objects.filter(
            fee=obj,
            action="UPDATE",
            status="PENDING"
        ).exists()

    def get_has_disable_pending(self, obj):
        return FeeChangeRequest.objects.filter(
            fee=obj,
            action="DISABLE",
            status="PENDING"
        ).exists()
    

class ExpenseDetailSerializer(serializers.ModelSerializer):
    supported_member = SimpleEdirUserSerializer(read_only=True)
    has_edit_pending = serializers.SerializerMethodField()
    has_disable_pending = serializers.SerializerMethodField()

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
            "has_edit_pending",
            "has_disable_pending",
        ]
    def get_has_edit_pending(self, obj):
        return ExpenseChangeRequest.objects.filter(
            fee=obj,
            action="UPDATE",
            status="PENDING"
        ).exists()

    def get_has_disable_pending(self, obj):
        return ExpenseChangeRequest.objects.filter(
            fee=obj,
            action="DISABLE",
            status="PENDING"
        ).exists()

class FeeWithAssignmentsSerializer(serializers.ModelSerializer):
    # assignments = FeeTrxSerializer(many=True, read_only=True)
    supported_member = SimpleUserSerializer(read_only=True)
    class Meta:
        model = Fee
        fields = ["id", "category", "amount", "reason", "payment_date", "supported_member"]

class ExpenseFeeSerializer(serializers.ModelSerializer):
    fee_id = serializers.IntegerField(source="trx.first.fee.id")
    name = serializers.CharField(source="trx.first.fee.name")
    category = serializers.CharField(source="trx.first.fee.category")
    amount = serializers.IntegerField(
        source="trx.first.fee.amount",
    ) #  max_digits=10, decimal_places=2
    status = serializers.CharField(source="trx.first.fee.status")
    supported_member = SimpleUserSerializer(source="trx.first.fee.supported_member", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "fee_id",
            "name",
            "category",
            "amount",
            "status",
            "supported_member",
        ]


class ExpenseChangeRequestSerializer(serializers.ModelSerializer):
    maker = SimpleEdirUserSerializer(read_only=True)
    fee = ExpenseDetailSerializer(read_only=True)

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

        return data


class PaymentChangeRequestSerializer(serializers.ModelSerializer):
    maker = SimpleEdirUserSerializer(read_only=True)
    user = SimpleEdirUserSerializer(read_only=True)
    # trx = TransactionDetailSerializer(read_only=True)

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

        # if new_value and new_value.get("bank"):
        #     bank_id = new_value["bank"]
        #     try:
        #         bank = Bank.objects.get(id=bank_id)
        #         new_value["bank"] = {
        #             "id": bank.id,
        #             "name": bank.bank_name
        #         }
        #     except Bank.DoesNotExist:
        #         pass
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


class FamilyDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Family
        fields = ['id', 'full_name', 'gender', 'relationship', 'profession']

class UserDetailSerializer(serializers.ModelSerializer):
    family = FamilyDetailSerializer(many=True, read_only=True)  
    number_of_family = serializers.SerializerMethodField()
    # is_committee = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'full_name',
            'phone_number',
            'gender',
            'marital_status',
            'profession',
            'address',
            'family',
            'number_of_family',
            # 'is_committee',
        ]
    def get_number_of_family(self, obj):
        return obj.family.count()

    # def get_is_committee(self, obj):
    #     return False

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

class TransactionSerializer(serializers.ModelSerializer):
    ref = serializers.CharField(source="reference")
    # bank_name = serializers.CharField(source="bank.bank_name", default=None)
    # image = serializers.SerializerMethodField()
    fees = FeeAssignmentSerializer(source="feeassignment_trx", many=True)
    
    has_edit_pending = serializers.SerializerMethodField()
    has_disable_pending = serializers.SerializerMethodField()
    maker = serializers.SerializerMethodField()

    total_amount = serializers.IntegerField(source="amount") #, max_digits=10, decimal_places=2
    class Meta:
        model = Transaction
        fields = [
            "ref",
            "created_at",
            "payment_method",
            # "bank_name",
            # "image",
            "total_amount",
            "payment_status",
            "fees",
            "has_edit_pending",
            "has_disable_pending",
            "maker",
        ]

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_has_edit_pending(self, obj):
        return TransactionChangeRequest.objects.filter(
            prev_trx=obj,
            action="UPDATE",
            status="PENDING"
        ).exists()

    def get_has_disable_pending(self, obj):
        return TransactionChangeRequest.objects.filter(
            trx=obj,
            action="DISABLE",
            status="PENDING"
        ).exists()

    def get_maker(self, obj):
        return TransactionChangeRequest.objects.filter(
            trx=obj).select_related("maker").values_list("maker__id", flat=True).first()
