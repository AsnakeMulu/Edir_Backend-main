from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('edirs/<int:edir_id>/members/', views.members_list_create, name='members-list-create'),
    path("edir/<int:edir_id>/members/", views.members_by_edir, name="members-by-edir"),
    path('admin-create-user/<int:edir_id>/', views.admin_create_user, name='admin-create-user'),
    path('add-existed-user/<int:edir_id>/', views.add_existed_user, name='add-existed-user'),
    path('check-user-in-edir/<int:edir_id>/<int:phone_number>/', views.check_user_in_edir, name='check-user-in-edir'),
    path('user/register/', views.self_register, name='user-register'),
    path("user/<int:user_id>/<int:edir_id>/deactivate/", views.deactivate_member, name="deactivate-member"),
    
    # path('user/<int:user_id>/<int:edir_id>/', views.user_detail, name='user-detail'),
    # path('user/<int:user_id>/', views.user_detail_with_family, name='user-detail_with_family'),
    
    path('user/<int:user_id>/', views.user_detail, name='user-detail'),
    path('user/<int:user_id>/<int:edir_id>/', views.user_detail, name='user-detail-with-edir'),
    path('set-password/<uidb64>/<token>/', views.set_password, name='set-password'),
    
    path('admin-add-family/<int:user_id>/', views.add_family, name='admin-add-family'),   
    path('family_list/<int:user_id>/', views.user_family_list, name='family-list'), 
    path('family/<int:user_id>/', views.family_detail, name='family-detail'), 
    path("family/<int:family_id>/deactivate/", views.deactivate_family, name="deactivate-family"),
    path('family/<int:family_id>/delete/', views.delete_family_member, name='delete-family'),

    path('add-bank/<int:edir_id>/', views.add_bank, name='add-bank'),   
    path('bank_list/<int:edir_id>/', views.edir_bank_list, name='bank-list'), 
    path('bank/<int:bank_id>/', views.bank_detail, name='bank-detail'), 
    path("bank/<int:bank_id>/deactivate/", views.deactivate_bank, name="deactivate-bank"),
    path('bank/<int:bank_id>/delete/', views.delete_bank, name='delete-bank'),

    path('add-event/<int:edir_id>/', views.add_event, name='add-event'),   
    path('event_list/<int:edir_id>/', views.edir_event_list, name='event-list'),
    path('popular_event/', views.popular_event_list, name='popular-event'),
    path('event/<int:event_id>/', views.event_detail, name='event-detail'), 
    path("event/<int:event_id>/deactivate/", views.deactivate_event, name="deactivate-event"),

    path('check_user_phone/<int:phone_number>/', views.check_user_phone, name='check_user_phone'),
    path('check_user_phoneNumber/<int:phone_number>/', views.check_user_phoneNumber, name='check_user_phoneNumber'),
    path('check_phone/', views.check_phone, name='check_phone'),
    path('set_new_password/', views.set_new_password, name='set_new_password'),
    path('auth/change-password/', views.change_password, name='change-password'),

    path("edir/add/", views.add_edir, name="add_edir"),
    path("user/", views.get_user_with_edirs, name="user-with-edirs"),
    path("popular_edirs/", views.get_popular_edirs, name="popular-edirs"),
    path("requested_edirs/", views.get_requested_edirs, name="requested-edirs"),
    path('join_edir/<int:edir_id>/', views.join_edir, name='join-edir'), 
    path('edir_request/<int:edir_id>/<str:status>', views.update_edir_request, name='update-edir-request'), 
    path('edir_cancel_request/<int:edir_id>/', views.cancel_edir_request, name='cancel-edir-request'),

    path("edir/list/", views.list_edirs, name="list_edirs"),
    path("payment/add/", views.add_payment, name="add_payment"),
    path("payment/my/", views.my_payments, name="my_payments"),
    path("payment/all/", views.all_payments, name="all_payments"),
    
    path("help/", views.get_helps, name="user-helps"),

    path("bill/generate/", views.generate_bill, name="generate-bill"),
    path("bills/<int:edir_id>/", views.user_bills, name="user-bills"),
    path("edir/<int:edir_id>/", views.edir_detail, name="edir-detail"),
    
    path("edir_details/<int:edir_id>/", views.edir_details, name="edir-details"),
    path("bills/summary/", views.bill_summary, name="bill-summary"),
    path("edir/withdrawal/<int:edir_id>/", views.get_edir_withdrawals, name="get-withdrawal"),
    
    path("deposit/details/<int:edir_id>/", views.get_deposit_details, name="get-deposit-details"),
    
    path("edir/deposit/<int:edir_id>/", views.get_deposit_summary, name="get-deposit"),
    path("expense/detail/<int:fee_id>/", views.get_expense_detail, name="get-expense-detail"),
    
    path("edir/<int:pk>/update_meeting/", views.update_meeting_date),

    path("edir/payments/", views.edir_payments, name="edir-payments"),
    path("fees/create/<int:edir_id>/", views.create_fee, name="create-fees"),
    path("fees/update/<int:fee_id>/", views.update_fee, name="update-fees"),
    path("fees/<int:edir_id>/", views.fees_by_edir, name="get-fees"),
    path("fees/unpaid/<int:edir_id>/<int:user_id>/", views.get_unpaid_fees, name="get_unpaid_fees"),
    
    path("fees/paid/<str:trx_ref>/", views.get_paid_fees, name="get_paid_fees"),
    path("pay/fees/", views.pay_fees, name="pay-fees"),
    path("admin_pay/fees/", views.admin_pay_fees, name="admin-pay-fees"),
    path("unpay/fees/", views.unpay_fees, name="unpay-fees"),
    
    path("withdraw/<int:edir_id>/", views.withdraw, name="withdraw"),
    path("expense/update/<int:fee_id>/", views.update_expense, name="update-expense"),
    path("fee/<int:id>/", views.get_fee_details, name="fee-details"),
    path("payment/<int:payment_id>/", views.get_payment_details, name="payment-details"),
    path("payments/<str:trx_ref>/", views.get_payments, name="get_payment"),
    path("fee/<int:fee_id>/deactivate/", views.deactivate_fee, name="deactivate-fee"),
    path("remove/payment/<str:trx_ref>/", views.remove_payment, name="remove_payment"),
    path("bill/pay/", views.pay_bill, name="pay-bill"),
    path("user/<int:edir_id>/payments/", views.user_payments, name="user_payments"),
    
    path("user/payments/<int:user_id>/<int:edir_id>/", views.get_user_payments, name="get_user_payments"),
    path("edir/<int:edir_id>/unpaid-months/", views.unpaid_months, name="unpaid_months"),
    path('bill/<int:bill_id>/delete/', views.delete_bill, name='delete-bill'),
    path('payment/<int:payment_id>/delete/', views.delete_payment, name='delete-payment'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)