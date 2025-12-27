from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer, UserSerializer as BaseUserSerializer
from rest_framework import serializers
from .models import CustomUser, Family, Payment, Edir, Bill, Fee, FeeAssignment, Bank, EdirUser, Help, Event
import calendar
from datetime import date
from django.db.models import Sum
from django.contrib.auth import password_validation

class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = CustomUser
        fields = ('id', 'phone_number', 'password', "re_password", 'full_name', "gender", "marital_status", "city", "specific_place")

    def validate_phone_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        if len(value) < 10 or len(value) > 15:
            raise serializers.ValidationError("Phone number must be between 10 and 15 digits.")
        return value
    def validate_full_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Full name cannot be empty.")
        return value
    
# class UserSerializer(BaseUserSerializer):
#     class Meta(BaseUserSerializer.Meta):
#         model = CustomUser
#         fields = ('id', 'phone_number', 'full_name')

class UserSerializer(serializers.ModelSerializer):
    number_of_family = serializers.SerializerMethodField()
    is_committee = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'full_name',
            'phone_number',
            'gender',
            'is_committee',
            'marital_status',
            'profession',
            'city',
            'specific_place',
            'number_of_family',
        ]

    def get_number_of_family(self, obj):
        # If the user is being returned from EdirUser context, obj won't have family.
        family = getattr(obj, "family", None)
        if family is None:
            return 0
        return family.filter(status="Active").count()

    def get_is_committee(self, obj):
        edir_id = self.context.get("edir_id")
        if not edir_id:
            return False
        membership = obj.groupmembership_set.filter(group__edir_id=edir_id).first()
        return membership.is_committee if membership else False


class UserEdirSerializer(serializers.ModelSerializer):
    user_status = serializers.CharField(source="status")
    id = serializers.CharField(source="user.id")
    full_name = serializers.CharField(source="user.full_name")
    phone_number = serializers.CharField(source="user.phone_number")
    gender = serializers.CharField(source="user.gender")
    marital_status = serializers.CharField(source="user.marital_status")
    profession = serializers.CharField(source="user.profession")
    city = serializers.CharField(source="user.city")
    specific_place = serializers.CharField(source="user.specific_place")
    number_of_family = serializers.SerializerMethodField()

    class Meta:
        model = EdirUser
        fields = [
            'id', 'full_name', 'phone_number',  'gender',  'is_committee',
            'marital_status', 'profession', 'city', 'specific_place', "number_of_family", "user_status"
        ] #'email',
    def get_number_of_family(self, obj):
        return obj.user.family.filter(status="Active").count()
        

class FamilySerializer(serializers.ModelSerializer):
    class Meta:
        model = Family
        fields = [
            'id', 'full_name', 'gender', 'profession', 'relationship', 'user',
            # add other fields you want to expose //'date_of_birth', 
        ]

class AddEdirSerializer(serializers.ModelSerializer):
    class Meta:
        model = Edir
        fields = [
            "id", "name", "monthly_fee", "city", "specific_place",
            "created_date", "meeting_date", "meeting_place",
        ]
        read_only_fields = ["id", "created_date", ]

#     # 👇 exclude users from being required in the request
#     users = serializers.PrimaryKeyRelatedField(read_only=True, many=True)

class EdirSerializer(serializers.ModelSerializer):
    # show users as read-only (list of IDs)
    users = serializers.PrimaryKeyRelatedField(read_only=True, many=True)

    class Meta:
        model = Edir
        fields = [
            "id",
            "name",
            "monthly_fee",
            # "country",
            "city",
            "specific_place",
            "created_date",
            "users",   # 👈 must be included here
        ]
        read_only_fields = ["id", "created_date", "users"]


class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = [
            'id', 'bank_name', 'account_number', 'account_name', 'edir',
        ]


class PaymentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)
    edir_name = serializers.CharField(source="edir.name", read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "user", "user_name", "edir", "edir_name", "month", "amount", "payment_date"]

class UserWithEdirsSerializer(serializers.ModelSerializer):
    edirs = EdirSerializer(many=True, read_only=True)

    class Meta:
        model = CustomUser
        fields = ["id", "full_name", "phone_number", "edirs"]
        read_only_fields = ["id", "edirs"]

class PaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Payment
        fields = "__all__"

class BillSerializer(serializers.ModelSerializer):
    bill = PaymentSerializer(read_only=True)
    class Meta:
        model = Bill
        fields = "__all__"

class EventSerializer(serializers.ModelSerializer):
    # bill = PaymentSerializer(read_only=True)
    class Meta:
        model = Event
        fields = "__all__"

class SemiBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = ["id", "month", "amount"]

class HelpSerializer(serializers.ModelSerializer):
    class Meta:
        model = Help
        fields = ["id", "question", "answer", "type"]

class PaymentDetailsSerializer(serializers.ModelSerializer):
    bills = SemiBillSerializer(source="payment", many=True)  # related_name="payment" from Bill model
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ["id", "method", "paid_at", "bills", "total_amount"]

    def get_total_amount(self, obj):
        return sum(bill.amount for bill in obj.payment.all())
    
class EdirSerializer2(serializers.ModelSerializer):
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

class EdirSerializer1(serializers.ModelSerializer):
    class Meta:
        model = Edir
        fields = [
            "id",
            "name",
            "monthly_fee",
            "city",
            "specific_place",
            "created_date",
            "meeting_date",
            "meeting_place",
        ]

    
class EdirDetailSerializer1(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    # unpaid_fees_total = serializers.SerializerMethodField()
    committee_members = serializers.SerializerMethodField()

    class Meta:
        model = Edir
        fields = [
            "id",
            "name",
            "monthly_fee",
            "city",
            "specific_place",
            "created_date",
            "member_count",
            # "unpaid_fees_total",
            "committee_members"
        ]

    def get_member_count(self, obj):
        # Count only active members in EdirUser
        return EdirUser.objects.filter(edir=obj, status="Active").count()

    # def get_unpaid_fees_total(self, obj):
    #     # Example: sum of unpaid fees for active members
    #     return sum(
    #         fee.amount for fee in obj.fee_set.filter(user__edirs=obj, paid=False)
    #     )

    def get_committee_members(self, obj):
        # Return a list of committee members' full names
        committee_users = EdirUser.objects.filter(edir=obj, is_committee=True)
        return [user.user.full_name for user in committee_users]

    
class EdirDetailSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    unpaid_fees_total = serializers.SerializerMethodField()
    committee_members = serializers.SerializerMethodField()

    class Meta:
        model = Edir
        fields = [
            "id", "name", "monthly_fee", "city", "specific_place", "meeting_date", "meeting_place",
            "created_date", "member_count", "unpaid_fees_total", "committee_members"
        ]
    # @staticmethod
    def get_member_count(self, obj):
        # return obj.users.count()
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
        # members = CustomUser.objects.filter(
        #     groupmembership__group__edir=obj,  # get group for this edir
        #     groupmembership__is_committee=True
        # # ).distinct()
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
        return UserSerializer(members, many=True).data

class BillSummarySerializer(serializers.Serializer):
    # edir_id = serializers.IntegerField()
    payment_date = serializers.DateField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class FeeAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeAssignment
        fields = "__all__"

class FeeSerializer(serializers.ModelSerializer):
    assignments = FeeAssignmentSerializer(many=True, read_only=True)

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

class FeeAssignmentsSerializer(serializers.ModelSerializer):
    fee_id = serializers.IntegerField(source="fee.id", read_only=True)
    fee_name = serializers.CharField(source="fee.name", read_only=True)
    fee_amount = serializers.DecimalField(source="fee.amount", max_digits=10, decimal_places=2, read_only=True)
    fee_category = serializers.CharField(source="fee.category", read_only=True)

    class Meta:
        model = FeeAssignment
        fields = ["id", "fee_name", "fee_id", "fee_amount", "fee_category", "payment_status", "paid_date"]

class WithdrawalSerializer(serializers.ModelSerializer):
    fee_name = serializers.CharField(source="fee.name", read_only=True)
    fee_amount = serializers.DecimalField(source="fee.amount", max_digits=10, decimal_places=2, read_only=True)
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)
    fee_transaction_type = serializers.CharField(source="fee.transaction_type", read_only=True)
    class Meta:
        model = FeeAssignment
        fields = ["id", "fee_name", "fee_amount", "user_full_name", "method", "fee_transaction_type", "payment_status"]

class FeeAssignmentDetailSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)
    fee_name = serializers.CharField(source="fee.name", read_only=True)
    fee_amount = serializers.DecimalField(source="fee.amount", max_digits=10, decimal_places=2, read_only=True)
    fee_category = serializers.CharField(source="fee.category", read_only=True)
    fee_reason = serializers.CharField(source="fee.reason", read_only=True)

    class Meta:
        model = FeeAssignment
        fields = [
            "id",
            "fee_name",
            "fee_amount",
            "fee_category",
            "fee_reason",
            # "transaction_type",
            "payment_status",
            "method",
            "paid_date",
            "Trx_ref",
            "user_full_name",
        ]
    def to_representation(self, instance):
        # Get the default serialized data
        data = super().to_representation(instance)

        # ✅ Replace null or empty user_full_name with "Edir"
        if not data.get("user_full_name"):
            data["user_full_name"] = "Edir"

        return data

class FeeAsignmentsSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = FeeAssignment
        fields = ["id", "user_full_name", "method", "Trx_ref", "payment_status", "paid_date"]
        

class FeeWithAssignmentsSerializer(serializers.ModelSerializer):
    assignments = FeeAsignmentsSerializer(many=True, read_only=True)

    class Meta:
        model = Fee
        fields = ["id", "name", "category", "amount", "reason", "payment_date", "transaction_type", "assignments"]

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
    family = FamilySerializer(many=True, read_only=True)  # related_name='family' in model
    number_of_family = serializers.SerializerMethodField()
    is_committee = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'full_name',
            'phone_number',
            'gender',
            'marital_status',
            'language',
            'profession',
            'city',
            'specific_place',
            'family',
            'number_of_family',
            'is_committee',
        ]
    def get_number_of_family(self, obj):
        return obj.family.count()

    def get_is_committee(self, obj):
        return False