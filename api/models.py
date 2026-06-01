from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
import uuid

GENDER_CHOICES = [
    ('Male', 'Male'),
    ('Female', 'Female'),
]

MARITAL_STATUS_CHOICES = [
    ('Single', 'Single'),
    ('Married', 'Married'),
    ('Divorced', 'Divorced'),
]
STATUS = [
        ('Active', 'Active'),
        ('Not Active', 'Not Active'),
    ]

class CustomUserManager(BaseUserManager):
    def create_user(
        self, phone_number, password=None, **extra_fields,
    ):
        if not phone_number:
            raise ValueError("The Phone Number must be set")

        user = self.model(
            phone_number=phone_number,
            **extra_fields
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number,  password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        # extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        # if extra_fields.get("is_superuser") is not True:
        #     raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(phone_number,  password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=15, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'

    def __str__(self):
        return self.phone_number
    

class UserChangeRequest(models.Model):
    ACTION_CHOICES = (
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DISABLE", "Disable"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CREATED", "Created"),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    maker = models.ForeignKey(CustomUser, related_name="user_maker", on_delete=models.CASCADE, null=True)
    checker = models.ForeignKey(CustomUser, related_name="user_checker", on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

class Edir(models.Model):
    users = models.ManyToManyField(CustomUser, related_name="user_edir", through="EdirUser", through_fields=("edir", "user"))
    name = models.CharField(max_length=100)
    monthly_fee = models.FloatField()
    address = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    meeting_date = models.DateField(blank=True, null=True)
    meeting_place = models.CharField(max_length=155, blank=True, null=True)
    is_popular = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS, default='Active')
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

class EdirUser(models.Model):
    STATUS_CHOICES = [
        ('Blocked', 'Blocked'),
        ('Active', 'Active'),
        ('Not Active', 'Not Active'),
        ('Leaved', 'Leaved'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    edir = models.ForeignKey(Edir, on_delete=models.SET_NULL, blank=True, null=True)
    phone_number = models.CharField(max_length=15)
    full_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True, null=True)
    profession = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(upload_to='images/', null=True, blank=True) 

    is_committee = models.BooleanField(default=False)
    leave_reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    joined_date = models.DateTimeField(null=True, blank=True)
    updated_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'edir')  # Prevent duplication

    def __str__(self):
        user_name = getattr(self, 'full_name', None) or getattr(self.user, 'phone_number', 'Unknown')
        edir_name = getattr(self.edir, 'name', 'No Edir') if self.edir else 'No Edir'
        return f"{user_name} - user id: {self.user.id} - edir name: {edir_name} - is_committee: {self.is_committee} - status: {self.status}"
    
class EdirUserChangeRequest(models.Model):
    ACTION_CHOICES = (
        ("JOIN_REQUEST", "Join Request"),
        ("LEAVE_REQUEST", "Leave Request"),
        ("ADD_MEMBER", "Add Member by Admin"),
        ("BLOCK_MEMBER", "Block Member"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CREATED", "Created"),
    )

    edir = models.ForeignKey(Edir, on_delete=models.SET_NULL, null=True, blank=True)
    edir_user = models.ForeignKey(EdirUser, on_delete=models.SET_NULL, blank=True, null=True)
    phone_number = models.CharField(max_length=15)

    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    comment = models.TextField(blank=True, null=True)

    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    maker = models.ForeignKey(
        EdirUser,
        related_name="edir_user_maker",
        on_delete=models.CASCADE,
        null=True,
    )

    checker = models.ForeignKey(
        EdirUser,
        related_name="edir_user_checker",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.full_name} - {self.action} - {self.status}" 

class EdirChangeRequest(models.Model):
    ACTION_CHOICES = (
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DISABLE", "Disable"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CREATED", "Created"),
    )

    edir = models.ForeignKey(Edir, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    maker = models.ForeignKey(EdirUser, related_name="edir_maker", on_delete=models.CASCADE, null=True)
    checker = models.ForeignKey(EdirUser, related_name="edir_checker", on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)


class Family(models.Model):
    RELATIONSHIP_CHOICES = [
        ('Partner', 'Partner'),
        ('Child', 'Child'),
        ('Parent', 'Parent'),
        ('Sibling', 'Sibling'),
        ('Partner Parent', 'Partner Parent'),
        ('Partner Sibling', 'Partner Sibling'),
    ]
    user = models.ForeignKey(EdirUser, on_delete=models.CASCADE, related_name='family', null=True, blank=True)
    full_name = models.CharField(max_length=255)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    relationship = models.CharField(max_length=50, choices=RELATIONSHIP_CHOICES)
    profession = models.CharField(max_length=100, blank=True, null=True)
    
    status = models.CharField(max_length=15, choices=STATUS, default="Active")
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        owner = self.user.full_name if self.user else self.full_name
        return f"{self.full_name} ({self.relationship} of {owner})"

 
class FamilyChangeRequest(models.Model):
    ACTION_CHOICES = (
        ("CREATE", "Create"),
        ("UPDATE", "UPDATE"),
        ("DISABLE", "Disable"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )

    family = models.ForeignKey(Family, on_delete=models.SET_NULL, null=True, blank=True)
    edir_user = models.ForeignKey(EdirUser, on_delete=models.CASCADE)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    comment = models.TextField(blank=True, null=True)

    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    maker = models.ForeignKey(
        EdirUser,
        related_name="family_maker",
        on_delete=models.CASCADE,
        null=True,
    )

    checker = models.ForeignKey(
        EdirUser,
        related_name="family_checker",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.full_name} - {self.action} - {self.status}"

class Bank(models.Model):
    # BANKS = [
    #     ('CBE', 'CBE'),
    #     ('Bank of Abyssinia', 'Bank of Abyssinia'),
    #     ('Awash Bank', 'Awash Bank'),
    #     ('Dashen Bank', 'Dashen Bank'),
    #     ('Hibret Bank', 'Hibret Bank'),
    #     ('Wegagen Bank', 'Wegagen Bank'),
    # ]
    STATUS = [
        ('Active', 'Active'),
        ('Not Active', 'Not Active'),
        ('Pending', 'Pending'),
        ('Rejected', 'Rejected'),
    ]

    edir = models.ForeignKey(Edir, on_delete=models.CASCADE, related_name='bank', null=True, blank=True)
    bank_name = models.CharField(max_length=50 ) #choices=BANKS
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=20)
    amount = models.IntegerField(default=0)
    
    status = models.CharField(max_length=15, choices=STATUS, default="Active")
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True, blank=True)

class BankChangeRequest(models.Model):
    ACTION_CHOICES = (
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DISABLE", "Disable"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CREATED", "Created"),
    )
    edir = models.ForeignKey(Edir, on_delete=models.CASCADE, null=True, blank=True)
    bank = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    maker = models.ForeignKey(EdirUser, related_name="bank_maker", on_delete=models.CASCADE, null=True)
    checker = models.ForeignKey(EdirUser, related_name="bank_checker", on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
class Fee(models.Model):
    CATEGORY = [
        ("Monthly Fee", "Monthly Fee"),
        ("Funeral Contribution", "Funeral Contribution"),
        ("Donation Contribution", "Donation Contribution"),
        ("Sickness Support", "Sickness Support"),
        ("Registration Fee", "Registration Fee"),
        ("Other", "Other"),
    ]
    STATUS = [
        ('Active', 'Active'),
        ('Not Active', 'Not Active'),
        # ('Completed', 'Completed'),
    ]
    Fee_Type = [
        ('Expense', 'Expense'),
        ('Income', 'Income'),
        ('Fee', 'Fee'),
    ]

    edir = models.ForeignKey("Edir", on_delete=models.CASCADE, related_name="fee_edir")
    name = models.CharField(max_length=100, blank=True, null=True) 
    supported_member = models.ForeignKey(
        EdirUser, related_name="fee_supported_member",
        on_delete=models.SET_NULL, null=True, blank=True
    )
    category = models.CharField(max_length=30, choices=CATEGORY, default="Monthly Fee")
    amount = models.IntegerField()
    reason = models.TextField(blank=True, null=True)

    fee_type = models.CharField(max_length=20, choices=Fee_Type, default="Fee")
    status = models.CharField(max_length=30, choices=STATUS, default="Active")
    payment_date = models.DateField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.category}, Supported Member = {self.supported_member}, {self.name}, {self.amount} Birr, reason = {self.reason}, Payment date - {self.payment_date}"
    

class ExpenseChangeRequest(models.Model):
    ACTION_CHOICES = (
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DISABLE", "Disable"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        # ("CREATED", "Created"),
    )
    edir = models.ForeignKey(Edir, on_delete=models.CASCADE, null=True, blank=True)
    fee = models.ForeignKey(Fee, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    maker = models.ForeignKey(EdirUser, related_name="expense_maker", on_delete=models.CASCADE, null=True)
    checker = models.ForeignKey(EdirUser, related_name="expense_checker", on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)


class IncomeChangeRequest(models.Model):
    ACTION_CHOICES = (
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DISABLE", "Disable"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        # ("CREATED", "Created"),
    )
    edir = models.ForeignKey(Edir, on_delete=models.CASCADE, null=True, blank=True)
    fee = models.ForeignKey(Fee, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    maker = models.ForeignKey(EdirUser, related_name="income_maker", on_delete=models.CASCADE, null=True)
    checker = models.ForeignKey(EdirUser, related_name="income_checker", on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)


class FeeChangeRequest(models.Model):
    ACTION_CHOICES = (
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DISABLE", "Disable"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        # ("CREATED", "Created"),
    )
    edir = models.ForeignKey(Edir, on_delete=models.CASCADE, null=True, blank=True)
    fee = models.ForeignKey(Fee, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    maker = models.ForeignKey(EdirUser, related_name="fee_maker", on_delete=models.CASCADE, null=True)
    checker = models.ForeignKey(EdirUser, related_name="fee_checker", on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

class Deposit(models.Model):
    TRANSACTION_TYPE = (
        ("WITHDRAW", "Withdraw"),
        ("PAYMENT", "Payment"),
    )
    TRANSACTION_METHOD = (
        ("CASH", "CASH"),
        ("TRANSFER", "TRANSFER"),
    )
    STATUS = (
        ("REVERSED", "Reversed"),
        ("Cancelled", "Cancelled"),
        ("Paid", "Paid")
    )

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE)
    payment_method = models.CharField(max_length=50, blank=True, null=True, choices=TRANSACTION_METHOD)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, related_name="bank", blank=True, null=True)
    user = models.ForeignKey(EdirUser, on_delete=models.CASCADE, related_name="deposit_user", null=True, blank=True)
    image = models.ImageField(upload_to='images/', null=True, blank=True) 
    
    payment_status = models.CharField(max_length=10, choices=STATUS, default="Paid")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

class DepositChangeRequest(models.Model):
    ACTION_CHOICES = (
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DISABLE", "Disable"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        # ("CREATED", "Created"),
    )
    edir = models.ForeignKey(Edir, on_delete=models.CASCADE, null=True, blank=True)
    deposit = models.ForeignKey(Deposit, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    maker = models.ForeignKey(EdirUser, related_name="deposit_maker", on_delete=models.CASCADE, null=True)
    checker = models.ForeignKey(EdirUser, related_name="deposit_checker", on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)


def generate_reference():
    return uuid.uuid4().hex[:16].upper()

class Transaction(models.Model):
    TRANSACTION_TYPE = (
        ("WITHDRAW", "Withdraw"),
        ("PAYMENT", "Payment"),
    )
    TRANSACTION_METHOD = (
        ("CASH", "CASH"),
        ("TRANSFER", "TRANSFER"),
    )
    STATUS = (
        ("REVERSED", "Reversed"),
        ("Cancelled", "Cancelled"),
        ("Paid", "Paid")
    )

    edir = models.ForeignKey(Edir, related_name="trx_edir", on_delete=models.CASCADE)
    reference = models.CharField(
        max_length=16,
        unique=True,
        editable=False,
        default=generate_reference
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE)
    amount = models.IntegerField()#max_digits=12, decimal_places=2
    payment_method = models.CharField(max_length=50, blank=True, null=True, choices=TRANSACTION_METHOD)
    deposit = models.ForeignKey(Deposit, on_delete=models.CASCADE, related_name="transactions", blank=True, null=True)
    user = models.ForeignKey(EdirUser, on_delete=models.CASCADE, related_name="trx_user", null=True, blank=True)
   
    payment_status = models.CharField(max_length=10, choices=STATUS, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)


class TransactionChangeRequest(models.Model):
    ACTION_CHOICES = (
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DISABLE", "Disable"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        # ("CREATED", "Created"),
    )
    edir = models.ForeignKey(Edir, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(EdirUser, related_name="trxrequest_user", on_delete=models.CASCADE, null=True, blank=True)
    trx = models.ForeignKey(Transaction, related_name="trx", on_delete=models.SET_NULL, null=True, blank=True)
    prev_trx = models.ForeignKey(Transaction, related_name="trx_prev", on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    maker = models.ForeignKey(EdirUser, related_name="trx_maker", on_delete=models.CASCADE, null=True)
    checker = models.ForeignKey(EdirUser, related_name="trx_checker", on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    comment = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='images/', null=True, blank=True) 

    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

class FeeAssignment(models.Model):
    STATUS_CHOICES = (
        ("Disabled", "Disabled"),
        ("Active", "Active"),
    )
    fee = models.ForeignKey(Fee, on_delete=models.CASCADE, related_name="feeassignment_fee")
    user = models.ForeignKey(EdirUser, on_delete=models.CASCADE, blank=True, null=True)
    transaction_change_request = models.ForeignKey(
        TransactionChangeRequest, on_delete=models.SET_NULL, null=True, blank=True
    )
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, related_name='feeassignment_trx', null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Active")
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True, blank=True)

class FeeAssignmentTrxChangeRequest(models.Model):
    fee_assignment = models.ForeignKey(FeeAssignment, on_delete=models.CASCADE)
    trx_change_request = models.ForeignKey(TransactionChangeRequest, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Event(models.Model):
    edir = models.ForeignKey("Edir", on_delete=models.CASCADE, related_name="event",  null=True, blank=True)
    made_by = models.ForeignKey(EdirUser, related_name="event", on_delete=models.CASCADE)
    title = models.CharField(max_length=100 ) 
    description = models.CharField(max_length=250 ) 
    caption = models.CharField(max_length=100, null=True, blank=True )
    location = models.CharField(max_length=100, null=True, blank=True ) 
    image = models.ImageField(upload_to='images/', null=True, blank=True) 
    
    date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS, default="Active")
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True, blank=True)

class Help(models.Model):
    CHOICES = [
    ('Common', 'Common'),
    ('FAQ', 'FAQ'),
]
    question = models.CharField(max_length=150)
    answer = models.CharField(max_length=250)
    type = models.CharField(max_length=50, choices=CHOICES, default="FAQ")
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.question} ({self.answer})"
