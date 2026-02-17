from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer, UserSerializer as BaseUserSerializer
from rest_framework import serializers
from .models import CustomUser, Family, Edir, Fee, FeeAssignment, Bank, EdirUser, Help, Event
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

class UserWithNumFamSerializer(serializers.ModelSerializer):
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
            'number_of_family',
            # 'is_committee',
        ]

    def get_number_of_family(self, obj):
        family = getattr(obj, "family", None)
        if family is None:
            return 0
        return family.filter(status="Active").count()

    # def get_is_committee(self, obj):
    #     edir_id = self.context.get("edir_id")
    #     if not edir_id:
    #         return False
    #     membership = obj.groupmembership_set.filter(group__edir_id=edir_id).first()
    #     return membership.is_committee if membership else False


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
    number_of_family = serializers.SerializerMethodField()

    class Meta:
        model = EdirUser #why???????????
        fields = [
            'id', 'full_name', 'phone_number',  'gender', 'marital_status', 
            'profession', 'address', "user_status", "number_of_family"
        ]
    def get_number_of_family(self, obj):
        return obj.user.family.filter(status="Active").count()
        

class FamilyWithUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Family
        fields = [
            'id', 'full_name', 'gender', 'profession', 'relationship', 'user'
        ]

# class AddEdirSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Edir
#         fields = [
#             "id", "name", "monthly_fee", "address", "description",
#             "created_date", "meeting_date", "meeting_place",
#         ]
#         read_only_fields = ["id", "created_date", ]


class EdirSerializer(serializers.ModelSerializer):
    meeting_date = serializers.DateField(
        input_formats=["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"],
        required=False,
        allow_null=True,
    )
    class Meta:
        model = Edir
        fields = [ 
            "created_by", 
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
            "created_by",
            "created_date",
            "updated_date",
            "is_popular",
            "status",
        )


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
    class Meta:
        model = Bank
        fields = [
            'id', 'bank_name', 'account_number', 'account_name', 'edir',
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
        total = (
            FeeAssignment.objects.filter(
                user=user,
                fee__edir=obj,
                fee__transaction_type="Deposit",
                payment_status="Not Paid",
            )
            .aggregate(total=Sum("fee__amount"))["total"]
        )
        return total or 0
    def get_committee_members(self, obj):
        # members = EdirUser.objects.filter(
        #     edir=obj,  # get group for this edir
        #     is_committee=True
        # ).distinct()
        committee_links = EdirUser.objects.filter(
            edir=obj,
            is_committee=True,
            status="Active"
        ).select_related("user")

        members = [link.user for link in committee_links]
        return UserWithNumFamSerializer(members, many=True).data

# class BillSummarySerializer(serializers.Serializer):
#     # edir_id = serializers.IntegerField()
#     payment_date = serializers.DateField()
#     total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class FeeAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeAssignment
        fields = "__all__"

class FeeSerializer(serializers.ModelSerializer):
    # assignments = FeeAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = Fee
        fields = "__all__"

# class TransactionSerializer(serializers.Serializer):
#     Trx_ref = serializers.CharField()
#     paid_date = serializers.DateTimeField()
#     method = serializers.CharField()
#     total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
#     fees = serializers.SerializerMethodField()

#     def get_fees(self, obj):
#         fees = FeeAssignment.objects.filter(Trx_ref=obj["Trx_ref"]).select_related("fee")
#         return FeeSerializer([f.fee for f in fees], many=True).data

class FeeAssignmentReadOnlySerializer(serializers.ModelSerializer):
    fee_id = serializers.IntegerField(source="fee.id", read_only=True)
    # fee_name = serializers.CharField(source="fee.name", read_only=True)
    fee_amount = serializers.DecimalField(source="fee.amount", max_digits=10, decimal_places=2, read_only=True)
    fee_category = serializers.CharField(source="fee.category", read_only=True)

    class Meta:
        model = FeeAssignment
        fields = ["fee_id", "fee_amount", "fee_category", "payment_status", "payment_date"]

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

class FeeAssignmentDetailSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)
    # fee_name = serializers.CharField(source="fee.name", read_only=True)
    fee_amount = serializers.DecimalField(source="fee.amount", max_digits=10, decimal_places=2, read_only=True)
    fee_category = serializers.CharField(source="fee.category", read_only=True)
    fee_reason = serializers.CharField(source="fee.reason", read_only=True)

    class Meta:
        model = FeeAssignment
        fields = [
            "id",
            # "fee_name",
            "fee_amount",
            "fee_category",
            "fee_reason",
            # "transaction_type",
            # "payment_status",
            # "payment_method",
            "payment_date",
            # "Trx_ref",
            "user_full_name",
        ]
    # def to_representation(self, instance):
    #     data = super().to_representation(instance)
    #     if not data.get("user_full_name"):
    #         data["user_full_name"] = "Edir"

    #     return data

class FeeTrxSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)
    trx_payment_method = serializers.CharField(source="trx.payment_method", read_only=True)
    trx_ref = serializers.CharField(source="trx.reference", read_only=True)
    trx_payment_status = serializers.CharField(source="trx.payment_status", read_only=True)
    trx_type = serializers.CharField(source="trx.transaction_type", read_only=True)

    class Meta:
        model = FeeAssignment
        fields = ["id", "user_full_name", "trx_payment_method", "trx_ref", "trx_type", "payment_status", "payment_date"]
        

class FeeWithAssignmentsSerializer(serializers.ModelSerializer):
    assignments = FeeTrxSerializer(many=True, read_only=True)

    class Meta:
        model = Fee
        fields = ["id", "category", "amount", "reason", "payment_date", "assignments"]

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