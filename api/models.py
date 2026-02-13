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

# class CustomUserManager(BaseUserManager):
#     def create_user(self, phone_number, full_name, password=None, gender = None, 
#                     marital_status = None, city = None, specific_place = None, **extra_fields):
#         if not phone_number:
#             raise ValueError('The Phone Number must be set')
#         user = self.model(phone_number=phone_number, full_name=full_name, gender = gender,
#                            marital_status = marital_status, city = city, specific_place = specific_place, **extra_fields)
#         user.set_password(password)
#         user.save(using=self._db)
#         return user
class CustomUserManager(BaseUserManager):
    def create_user(
        self, phone_number, full_name, password=None,
        gender=None, marital_status=None, city=None,
        specific_place=None, **extra_fields
    ):
        if not phone_number:
            raise ValueError("The Phone Number must be set")

        user = self.model(
            phone_number=phone_number,
            full_name=full_name,
            gender=gender,
            marital_status=marital_status,
            city=city,
            specific_place=specific_place,
            **extra_fields
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, full_name, password=None, gender = None, 
                    marital_status = None, city = None, specific_place = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(phone_number, full_name, password, gender = gender,
                           marital_status = marital_status, city = city, specific_place = specific_place, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, unique=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True, null=True)
    profession = models.CharField(max_length=100, blank=True, null=True)
    # email = models.EmailField( blank=True, null=True) #unique=True,
    address = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['full_name']

    def __str__(self):
        return self.phone_number
    

class UserAuditLog(models.Model):
    ACTION_CHOICES = (
        ("CREATED", "Created"),
        ("MODIFIED", "Modified"),
        ("Disabled", "Disabled"),
    )
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="userLogs"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True
    )
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.full_name} - {self.action}"


class Family(models.Model):
    RELATIONSHIP_CHOICES = [
        ('Partner', 'Partner'),
        ('Child', 'Child'),
        ('Parent', 'Parent'),
        ('Sibling', 'Sibling'),
        ('Partner Parent', 'Partner Parent'),
        ('Partner Sibling', 'Partner Sibling'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='family', null=True, blank=True)
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


class FamilyAuditLog(models.Model):
    ACTION_CHOICES = (
        ("CREATED", "Created"),
        ("MODIFIED", "Modified"),
        ("Loaded","Loaded")
        ("Disabled", "Disabled"),
    )
    family = models.ForeignKey(
        Family, on_delete=models.CASCADE, related_name="familyLogs"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True
    )
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.family.full_name} - {self.action}"



class EdirFamily(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Rejected', 'Rejected'),
        ('Cancelled', 'Cancelled'),
        ('Blocked', 'Blocked'),
        ('Active', 'Active'),
        ('Not Active', 'Not Active'),
    ]

    family = models.ForeignKey(Family, on_delete=models.CASCADE)
    edir = models.ForeignKey("Edir", on_delete=models.CASCADE)
    maker = models.ForeignKey(
        CustomUser, related_name="added_by", on_delete=models.CASCADE
    )
    checker = models.ForeignKey(
        CustomUser, related_name="checked_by",
        on_delete=models.SET_NULL, null=True, blank=True
    )
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    joined_date = models.DateTimeField(null=True, blank=True)
    updated_date = models.DateTimeField(null=True, blank=True)

    # class Meta:
    #     db_table = "customuser_edirs"
    #     unique_together = ('user', 'edir')  # Prevent duplication

    def __str__(self):
        return f"{self.family.full_name} - {self.edir.name} ({self.status})"
    

class EdirFamilyAuditLog(models.Model):
    ACTION_CHOICES = (
        ("CREATED", "Created"),
        ("MODIFIED", "Modified"),
        ("Disabled", "Disabled"),
    )
    edirFamily = models.ForeignKey(
        EdirFamily, on_delete=models.CASCADE, related_name="edirFamilyLogs"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True
    )
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.edirFamily.family.full_name} - {self.action}"


class Edir(models.Model):
    users = models.ManyToManyField(CustomUser, related_name="edirs", through="EdirUser")
    name = models.CharField(max_length=100)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2)
    # country = models.CharField(max_length=100, blank=True, null=True)
    # city = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    meeting_date = models.DateField(blank=True, null=True)
    meeting_place = models.CharField(max_length=155, blank=True, null=True)
    is_popular = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True
    )
    status = models.CharField(max_length=20, choices=STATUS, default='Active')
    created_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.name


class EdirAuditLog(models.Model):
    ACTION_CHOICES = (
        ("CREATED", "Created"),
        ("MODIFIED", "Modified"),
        ("Disabled", "Disabled"),
        ("BLOCKED", "Blocked"),
    )
    edir = models.ForeignKey(
        Edir, on_delete=models.CASCADE, related_name="edirLogs"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True
    )
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.edir.name} - {self.action}"
    

class EdirUser(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Rejected', 'Rejected'),
        ('Cancelled', 'Cancelled'),
        ('Blocked', 'Blocked'),
        ('Active', 'Active'),
        ('Not Active', 'Not Active'),
        ('Leaved', 'Leaved'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    edir = models.ForeignKey("Edir", on_delete=models.CASCADE)
    is_committee = models.BooleanField(default=False)
    maker = models.ForeignKey(
        CustomUser, related_name="added_by", on_delete=models.CASCADE
    )
    checker = models.ForeignKey(
        CustomUser, related_name="checked_by",
        on_delete=models.SET_NULL, null=True, blank=True
    )
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    joined_date = models.DateTimeField(null=True, blank=True)
    updated_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        # db_table = "customuser_edirs"
        unique_together = ('user', 'edir')  # Prevent duplication

    def __str__(self):
        return f"{self.user.full_name} - {self.edir.name} ({self.status})"
    

class EdirUserAuditLog(models.Model):
    ACTION_CHOICES = (
        ("CREATED", "Created"),
        ("MODIFIED", "Modified"),
        ("Disabled", "Disabled"),
        ("BLOCKED", "Blocked"),
        ("Leaved", "Leaved"),
    )
    edirUser = models.ForeignKey(
        EdirUser, on_delete=models.CASCADE, related_name="edirUserLogs"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True
    )
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.edirUser.user.full_name} - {self.action}"

    
# class CustomGroup(models.Model):
#     name = models.CharField(max_length=150, unique=True)
#     edir = models.ForeignKey(Edir, on_delete=models.CASCADE, related_name="groups")

#     def __str__(self):
#         return f"{self.name} ({self.edir.name})"


# class GroupMembership(models.Model):  # 👈 explicit join table
#     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
#     group = models.ForeignKey(CustomGroup, on_delete=models.CASCADE)
#     is_committee = models.BooleanField(default=False)
#     joined_at = models.DateTimeField(auto_now_add=True)  # optional extra field

#     class Meta:
#         db_table = "customuser_groups"  # 👈 single table name
#         unique_together = ("user", "group")


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
    maker = models.ForeignKey(
        CustomUser, related_name="bank_maker", on_delete=models.CASCADE
    )
    checker = models.ForeignKey(
        CustomUser, related_name="bank_checker",
        on_delete=models.SET_NULL, null=True, blank=True
    )
    status = models.CharField(max_length=15, choices=STATUS, default="Active")
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True, blank=True)

    
class BankAuditLog(models.Model):
    ACTION_CHOICES = (
        ("CREATED", "Created"),
        ("MODIFIED", "Modified"),
        ("Disabled", "Disabled"),
    )
    # STATUS_CHOICES = (
    #     ('Pending', 'Pending'),
    #     ('Approved', 'Approved'),
    #     ('Rejected', 'Rejected'),
    #     # ("CANCELLED", "Cancelled"),
    # )
    bank = models.ForeignKey(
        Bank, on_delete=models.CASCADE, related_name="bankLogs"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True
    )
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bank.bank_name} - {self.action}"


# class Payment(models.Model):
#     paid_at = models.DateTimeField(auto_now_add=True)
#     method = models.CharField(max_length=50, blank=True, null=True)  
    
#     reason = models.TextField()
#     is_paid = models.BooleanField(default=False)

# class Bill(models.Model):
#     TRANSACTION_TYPES = [
#         ('Deposit', 'Deposit'),
#         ('Withdrawal', 'Withdrawal'),
#     ]
#     user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.CASCADE, related_name="payments")
#     edir = models.ForeignKey(Edir, on_delete=models.CASCADE, related_name="payments")
#     payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="payments")
#     month = models.CharField(max_length=20, null=True, blank=True)  # e.g. "January 2025"
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES)
#     payment_date = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.user} - {self.month} - {self.amount} Birr"
    
class Fee(models.Model):
    CATEGORY = [
        ("Monthly Fee", "Monthly Fee"),
        ("Funeral Contribution", "Funeral Contribution"),
        ("Sickness Support", "Sickness Support"),
        ("Registration Fee", "Registration Fee"),
        ("Other", "Other"),
    ]

    edir = models.ForeignKey("Edir", on_delete=models.CASCADE, related_name="fees")
    # name = models.CharField(max_length=100, blank=True, null=True) 
    category = models.CharField(max_length=30, choices=CATEGORY, default="Monthly Fee")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField(blank=True, null=True)

    maker = models.ForeignKey(
        CustomUser, related_name="fee_maker", on_delete=models.CASCADE
    )
    checker = models.ForeignKey(
        CustomUser, related_name="fee_checker",
        on_delete=models.SET_NULL, null=True, blank=True
    )

    status = models.CharField(max_length=15, choices=STATUS, default="Active")
    payment_date = models.DateTimeField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.amount} Birr ({self.name})"
    

class FeeAuditLog(models.Model):
    ACTION_CHOICES = (
        ("CREATED", "Created"),
        ("MODIFIED", "Modified"),
        ("Disabled", "Disabled"),
        # ("CANCELLED", "Cancelled"),
    )
    fee = models.ForeignKey(
        Fee, on_delete=models.CASCADE, related_name="feeLogs"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True
    )
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    # comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.fee.category} - {self.action}"
    

class FeeAssignment(models.Model):
    fee = models.ForeignKey(Fee, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, blank=True, null=True)
    maker = models.ForeignKey(
        CustomUser, related_name="assigned_by", on_delete=models.CASCADE
    )
    created_date = models.DateTimeField(auto_now_add=True)

    
# class FeeAssignAuditLog(models.Model):
#     ACTION_CHOICES = (
#         ("CREATED", "Created"),
#         # ("MODIFIED", "Modified"),
#         ("REMOVED", "Removed"),
#         # ("CANCELLED", "Cancelled"),
#     )

#     feeAssign = models.ForeignKey(
#         FeeAssignment, on_delete=models.CASCADE, related_name="feeAssignLogs"
#     )
#     action = models.CharField(max_length=20, choices=ACTION_CHOICES)
#     performed_by = models.ForeignKey(
#         CustomUser, on_delete=models.SET_NULL, null=True
#     )

#     # previous_status = models.CharField(max_length=20)
#     # new_status = models.CharField(max_length=20)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.feeAssign.user} - {self.action}"

class Transaction(models.Model):
    TRANSACTION_TYPE = (
        ("WITHDRAW", "Withdraw"),
        ("PAYMENT", "Payment"),
    )
    STATUS = (
        ("PENDING", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )

    feeAssignment = models.ForeignKey(FeeAssignment, on_delete=models.CASCADE, related_name="feeAssignments")
    reference = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=50, blank=True, null=True) 
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, related_name="bank", blank=True, null=True)
    image = models.ImageField(upload_to='images/', null=True, blank=True) 
    maker = models.ForeignKey(
        CustomUser, related_name="made_by", on_delete=models.CASCADE
    )
    checker = models.ForeignKey(
        CustomUser, related_name="checked_by",
        on_delete=models.SET_NULL, null=True, blank=True
    )

    payment_status = models.CharField(max_length=10, choices=STATUS, default="PENDING")
    reason = models.TextField(blank=True, null=True)  # for rejection
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)


class TrxAuditLog(models.Model):
    ACTION_CHOICES = (
        ("CREATED", "Created"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    )
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="trxLogs"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True
    )

    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)

    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction.reference} - {self.action}"

class Event(models.Model):
    edir = models.ForeignKey("Edir", on_delete=models.CASCADE, related_name="event",  null=True, blank=True)
    made_by = models.ForeignKey(CustomUser, related_name="event", on_delete=models.CASCADE)
    title = models.CharField(max_length=100 ) 
    description = models.CharField(max_length=250 ) 
    caption = models.CharField(max_length=100, null=True, blank=True )
    location = models.CharField(max_length=100, null=True, blank=True ) 
    image = models.ImageField(upload_to='images/', null=True, blank=True) 
    
    date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS, default="Active")
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True, blank=True)


class EventAuditLog(models.Model):
    ACTION_CHOICES = (
        ("CREATED", "Created"),
        ("MODIFIED", "Modified"),
        ("DISABLED", "Disabled"),
        # ("CANCELLED", "Cancelled"),
    )

    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="eventLogs"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True
    )
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event.title} - {self.action}"

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
