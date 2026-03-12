from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    #User and Member related endpoints
    path('edirs/<int:edir_id>/members/', views.members_list_create, name='members-list-create'),
    path('members/<int:edir_id>/active/', views.active_members_list, name='active-members-list'),
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
    
    path('check_user_phone/<int:phone_number>/', views.check_user_phone, name='check_user_phone'),
    path('check_user_phoneNumber/<int:phone_number>/', views.check_user_phoneNumber, name='check_user_phoneNumber'),
    path('check_phone/', views.check_phone, name='check_phone'),
    path('set_new_password/', views.set_new_password, name='set_new_password'),
    path('auth/change-password/', views.change_password, name='change-password'),
    
    #Family related endpoints
    path('admin-add-family/<int:user_id>/', views.add_family, name='admin-add-family'),   
    path('family_list/<int:user_id>/', views.user_family_list, name='family-list'), 
    path('family/<int:user_id>/', views.family_detail, name='family-detail'), 
    path("family/<int:family_id>/deactivate/", views.deactivate_family, name="deactivate-family"),
    path('family/<int:family_id>/delete/', views.delete_family_member, name='delete-family'),

    #Bank account related endpoints
    path('add-bank/<int:edir_id>/', views.add_bank, name='add-bank'),   
    path('bank_list/<int:edir_id>/', views.edir_bank_list, name='bank-list'), 
    path('active_bank_list/<int:edir_id>/', views.edir_active_bank_list, name='active-bank-list'), 
    path('bank/<int:bank_id>/', views.bank_detail, name='bank-detail'), 
    path('update_bank/<int:bank_id>/', views.update_bank, name='update-bank'), 
    path("bank/<int:bank_id>/deactivate/", views.deactivate_bank, name="deactivate-bank"),
    path('bank/<int:bank_id>/delete/', views.delete_bank, name='delete-bank'),
    path('approve_bank/<int:id>/', views.approve_bank, name='approve-bank'),
    path('reject_bank/<int:id>/', views.reject_bank, name='reject-bank'),

    #Edir related endpoints
    path("edir/add/", views.add_edir, name="add_edir"),
    path("user/", views.get_user_with_edirs, name="user-with-edirs"),
    path("popular_edirs/", views.get_popular_edirs, name="popular-edirs"),
    path("requested_edirs/", views.get_requested_edirs, name="requested-edirs"),
    path('join_edir/<int:edir_id>/', views.join_edir, name='join-edir'), 
    path('edir_request/<int:edir_id>/<str:status>', views.update_edir_request, name='update-edir-request'), 
    path('edir_cancel_request/<int:edir_id>/', views.cancel_edir_request, name='cancel-edir-request'),
    path("edir/list/", views.list_edirs, name="list_edirs"),

    path("edir/<int:edir_id>/", views.dashboard, name="edir-detail"),
    path("edir/detail/<int:edir_id>/", views.edir_detail, name="edir-detail"),
    path("edir/update/<int:edir_id>/", views.update_edir, name="update-edir"),
    path("edir_details/<int:edir_id>/", views.edir_details, name="edir-details"),
    path("edir/approve_edit/<int:id>/", views.approve_edir_edit, name="approve_edir_edit"),
    path("edir/reject_edit/<int:id>/", views.reject_edir_edit, name="reject_edir_edit"),
    path("edir/<int:pk>/update_meeting/", views.update_meeting_date, name="update-meeting-date"),

    #Expense related endpoint
    path("edir/expenses/<int:edir_id>/", views.get_edir_expenses, name="get-expenses"),
    path("expense/detail/<int:fee_id>/", views.get_expense_detail, name="get-expense-detail"),
    path("add_expense/<int:edir_id>/", views.add_expense, name="add-expense"),
    path("expense/update/<int:fee_id>/", views.update_expense, name="update-expense"),
    path('approve_expense/<int:expense_id>/', views.approve_expense, name='approve-expense'),
    path('reject_expense/<int:expense_id>/', views.reject_expense, name='reject-expense'),

    path("incomes/details/<int:edir_id>/", views.get_daily_incomes_details, name="get-incomes-details"),
    # path("edir/incomes/<int:edir_id>/", views.get_edir_incomes, name="get-edir-incomes"),
    path("edir/incomes/<int:edir_id>/", views.get_daily_edir_incomes, name="get-daily-edir-incomes"),

    #Fee related endpoints
    path("fees/create/<int:edir_id>/", views.create_fee, name="create-fees"),
    path("fees/update/<int:fee_id>/", views.update_fee, name="update-fees"),
    path("fees/<int:edir_id>/", views.get_edir_fees, name="get-edir-fees"),
    path("fees/unpaid/<int:edir_id>/<int:user_id>/", views.get_unpaid_fees, name="get_unpaid_fees"),
    path("fees/paid/<str:trx_ref>/", views.get_paid_fees, name="get_paid_fees"),
    path("pay/fees/<int:edir_id>/", views.pay_fees, name="pay-fees"),
    path("admin_pay/fees/", views.admin_pay_fees, name="admin-pay-fees"),
    path("unpay/fees/", views.unpay_fees, name="unpay-fees"),
    path("fee_detail/<int:id>/", views.get_fee_details, name="fee-details"),
    path("fee/<int:fee_id>/deactivate/", views.deactivate_fee, name="deactivate-fee"),

    #Payment related endpoints
    path("payment_details/<str:ref>/", views.get_payment_detail, name="get_payment_detail"),
    path("remove/payment/<str:trx_ref>/", views.remove_payment, name="remove_payment"),
    path("user/payments/<int:user_id>/<int:edir_id>/", views.get_user_payments, name="get_user_payments"),
    # path("payment/<int:payment_id>/", views.get_payment_details, name="payment-details"),
    # path("edir/<int:edir_id>/unpaid-months/", views.unpaid_months, name="unpaid_months"),
    # path('bill/<int:bill_id>/delete/', views.delete_bill, name='delete-bill'),
    # path('payment/<int:payment_id>/delete/', views.delete_payment, name='delete-payment'),
    # path("bill/pay/", views.pay_bill, name="pay-bill"),
    # path("user/<int:edir_id>/payments/", views.user_payments, name="user_payments"),
    # path("payment/add/", views.add_payment, name="add_payment"),
    # path("payment/my/", views.my_payments, name="my_payments"),
    # path("payment/all/", views.all_payments, name="all_payments"),
    # path("edir/payments/", views.edir_payments, name="edir-payments"),
    
    #Event related endpoints
    path('add-event/<int:edir_id>/', views.add_event, name='add-event'),   
    path('event_list/<int:edir_id>/', views.edir_event_list, name='event-list'),
    path('popular_event/', views.popular_event_list, name='popular-event'),
    path('event/<int:event_id>/', views.event_detail, name='event-detail'), 
    path("event/<int:event_id>/deactivate/", views.deactivate_event, name="deactivate-event"),
    
    path("help/", views.get_helps, name="user-helps"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)