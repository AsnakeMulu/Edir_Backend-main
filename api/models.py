from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

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
        # ('Pending', 'Pending'),
        # ('Rejected', 'Rejected'),
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
    
    # edir = models.ForeignKey(Edir, on_delete=models.CASCADE, related_name="user", blank=True, null=True)
    # date_of_birth = models.DateField(blank=True, null=True)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True, null=True)
    # language = models.CharField(max_length=50, blank=True, null=True)
    profession = models.CharField(max_length=100, blank=True, null=True)
    # email = models.EmailField( blank=True, null=True) #unique=True,
    # country = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    specific_place = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    # is_committe = models.BooleanField(default=False)
    # status = models.CharField(max_length=15, choices=STATUS, default="Active")
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['full_name']

    def __str__(self):
        return self.phone_number

# class Partner(models.Model):
#     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='partner')
#     full_name = models.CharField(max_length=255)
    # phone_number = models.CharField(max_length=20, unique=True)
    # gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    # date_of_birth = models.DateField()
    # profession = models.CharField(max_length=100, blank=True, null=True)
    # email = models.EmailField(unique=True)
    # country = models.CharField(max_length=100)
    # city = models.CharField(max_length=100)
    # specific_place = models.CharField(max_length=255)

    # def __str__(self):
    #     return f"{self.full_name} (Partner of {self.user.full_name})"


class Family(models.Model):
    RELATIONSHIP_CHOICES = [
        ('Partner', 'Partner'),
        ('Child', 'Child'),
        ('Parent', 'Parent'),
        ('Sibling', 'Sibling'),
        ('Partner Parent', 'Partner Parent'),
        ('Partner Sibling', 'Partner Sibling'),
    ]
    # STATUS = [
    #     ('Active', 'Active'),
    #     ('Not Active', 'Not Active'),
    # ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='family', null=True, blank=True)
    # partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='family_members', null=True, blank=True)
    full_name = models.CharField(max_length=255)
    # phone_number = models.CharField(max_length=20, unique=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    # date_of_birth = models.DateField()
    relationship = models.CharField(max_length=50, choices=RELATIONSHIP_CHOICES)
    profession = models.CharField(max_length=100, blank=True, null=True)
    
    status = models.CharField(max_length=15, choices=STATUS, default="Active")
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        owner = self.user.full_name if self.user else self.full_name
        return f"{self.full_name} ({self.relationship} of {owner})"


class Edir(models.Model):
    users = models.ManyToManyField(CustomUser, related_name="edirs", through="EdirUser")
    name = models.CharField(max_length=100)
    created_date = models.DateField(auto_now_add=True)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2)
    # country = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    specific_place = models.CharField(max_length=255, blank=True, null=True)
    meeting_date = models.DateField(blank=True, null=True)
    meeting_place = models.CharField(max_length=155, blank=True, null=True)
    is_popular = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS, default='Active')

    def __str__(self):
        return self.name
    
class CustomGroup(models.Model):
    name = models.CharField(max_length=150, unique=True)
    edir = models.ForeignKey(Edir, on_delete=models.CASCADE, related_name="groups")

    def __str__(self):
        return f"{self.name} ({self.edir.name})"
    
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


class GroupMembership(models.Model):  # 👈 explicit join table
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    group = models.ForeignKey(CustomGroup, on_delete=models.CASCADE)
    is_committee = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)  # optional extra field

    class Meta:
        db_table = "customuser_groups"  # 👈 single table name
        unique_together = ("user", "group")

class EdirUser(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Rejected', 'Rejected'),
        ('Cancelled', 'Cancelled'),
        ('Active', 'Active'),
        ('Not Active', 'Not Active'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    edir = models.ForeignKey("Edir", on_delete=models.CASCADE)
    is_committee = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    joined_date = models.DateTimeField(null=True, blank=True)
    updated_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "customuser_edirs"
        unique_together = ('user', 'edir')  # Prevent duplication

    def __str__(self):
        return f"{self.user.full_name} - {self.edir.name} ({self.status})"


class Bank(models.Model):
    # BANKS = [
    #     ('CBE', 'CBE'),
    #     ('Bank of Abyssinia', 'Bank of Abyssinia'),
    #     ('Awash Bank', 'Awash Bank'),
    #     ('Dashen Bank', 'Dashen Bank'),
    #     ('Hibret Bank', 'Hibret Bank'),
    #     ('Wegagen Bank', 'Wegagen Bank'),
    # ]
    # STATUS = [
    #     ('Active', 'Active'),
    #     ('Not Active', 'Not Active'),
    # ]

    edir = models.ForeignKey(Edir, on_delete=models.CASCADE, related_name='bank', null=True, blank=True)
    bank_name = models.CharField(max_length=50 ) #choices=BANKS
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=20)
    status = models.CharField(max_length=15, choices=STATUS, default="Active")
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True, blank=True)

class Payment(models.Model):
    paid_at = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=50, blank=True, null=True)  
    
    reason = models.TextField()
    is_paid = models.BooleanField(default=False)

class Bill(models.Model):
    TRANSACTION_TYPES = [
        ('Deposit', 'Deposit'),
        ('Withdrawal', 'Withdrawal'),
    ]
    user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.CASCADE, related_name="payments")
    edir = models.ForeignKey(Edir, on_delete=models.CASCADE, related_name="payments")
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="payments")
    month = models.CharField(max_length=20, null=True, blank=True)  # e.g. "January 2025"
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES)
    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.month} - {self.amount} Birr"
    
class Fee(models.Model):
    CATEGORY = [
        ("Monthly Fee", "Monthly Fee"),
        ("Funeral Contribution", "Funeral Contribution"),
        ("Sickness Support", "Sickness Support"),
        ("Registration Fee", "Registration Fee"),
        ("Other", "Other"),
    ]
    TRANSACTION_TYPES = [
        ('Deposit', 'Deposit'),
        ('Withdrawal', 'Withdrawal'),
    ]
    # STATUS = [
    #     ('Active', 'Active'),
    #     ('Not Active', 'Not Active'),
    # ]

    edir = models.ForeignKey("Edir", on_delete=models.CASCADE, related_name="fees")
    name = models.CharField(max_length=100, blank=True, null=True) 
    category = models.CharField(max_length=30, choices=CATEGORY, default="Monthly Fee")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField(blank=True, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)#blank=True, null=True
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES, default="Deposit")

    payment_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default="Active")
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True, blank=True)
    # users = models.ManyToManyField( CustomUser, related_name="fees")

    def __str__(self):
        return f"{self.name} - {self.amount} Birr ({self.name})"
    

class FeeAssignment(models.Model):
    fee = models.ForeignKey(Fee, on_delete=models.CASCADE, related_name="assignments")
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, related_name="bank", blank=True, null=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, blank=True, null=True)
    method = models.CharField(max_length=50, blank=True, null=True) 
    Trx_ref = models.CharField(max_length=20, null=True, blank=True, db_index=True) 
    image = models.ImageField(upload_to='images/', null=True, blank=True) 
    payment_status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Paid", "Paid"), ("Not Paid", "Not Paid"), ("For You", "For You")],
        default="Not Paid",
    )
    paid_date = models.DateTimeField(blank=True, null=True)


class Event(models.Model):
    edir = models.ForeignKey("Edir", on_delete=models.CASCADE, related_name="event",  null=True, blank=True)
    # user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, blank=True, null=True)
    title = models.CharField(max_length=100 ) 
    description = models.CharField(max_length=250 ) 
    caption = models.CharField(max_length=100, null=True, blank=True )
    location = models.CharField(max_length=100, null=True, blank=True ) 
    image = models.ImageField(upload_to='images/', null=True, blank=True) 
    
    date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS, default="Active")
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(null=True, blank=True)
