from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    #User and Member related endpoints
    path('edir/<int:edir_id>/members/', views.members_list, name='members-list'), # Members
    path('edir/<int:edir_id>/member_requests/', views.member_requests, name='member-requests'), # Member requests
    path('member_request/<int:user_id>/', views.member_request, name='member-request'),
    path('members/<int:edir_id>/active/', views.active_members_list, name='active-members-list'), #Add Fee, Expense and Income
    path('admin-create-user/<int:edir_id>/', views.admin_create_user, name='admin-create-user'), # New member
    path('check-user-in-edir/<int:edir_id>/<int:phone_number>/', views.check_user_in_edir, name='check-user-in-edir'), #New Member
    path('user/register/', views.self_register, name='user-register'), # Registration
    path("member/update/<int:member_id>/", views.update_member, name="update-member"), # New Member form
    path("member/disable/<int:member_id>/", views.deactivate_member, name="deactivate-member"), #Member details
    path('approve_member/<int:id>/', views.approve_member, name='approve-member'), # Member approve request
    path('reject_member/<int:id>/', views.reject_member, name='reject-member'), # Member reject request
    path('member/cancel/<int:id>/', views.cancel_member, name='cancel-member'), # Member cancel request
    path("member_requests/count/<int:edir_id>/",views.member_request_count,name="member-request-count"),
    
    path('user/<int:user_id>/', views.user_detail, name='user-detail'), # change password and user context
    path('user/<int:user_id>/<int:edir_id>/', views.user_detail, name='user-detail-with-edir'), # change password and user context
    path('member_details/<int:user_id>/', views.member_details, name='member-details'), #member details
    path('check_user_phone/<int:phone_number>/', views.check_user_phone, name='check_user_phone'), # login and registration
    path('check_phone/', views.check_phone, name='check_phone'), # login
    path('set_new_password/', views.set_new_password, name='set_new_password'), # login
    path('auth/change-password/', views.change_password, name='change-password'), # change phone number
    
    #Family related endpoints
    path('admin_add_family/<int:user_id>/', views.add_family, name='admin-add-family'),   
    path('family_list/<int:user_id>/', views.user_family_list, name='family-list'), 
    path('family_requests/<int:user_id>/', views.user_family_requests, name='family-requests'), 
    path('family/<int:family_id>/', views.family_detail, name='family-detail'), 
    path("family/deactivate/<int:family_id>/", views.deactivate_family, name="deactivate-family"),
    path('approve_family/<int:id>/', views.approve_family, name='approve-family'),
    path('reject_family/<int:id>/', views.reject_family, name='reject-family'),
    path('family/cancel/<int:id>/', views.cancel_family, name='cancel-family'),

    #Edir related endpoints
    path("edir/add/", views.add_edir, name="add_edir"), #New Edir
    path("user/", views.get_user_with_edirs, name="user-with-edirs"), # Dashboard
    path("user_edirs/", views.get_user_edirs, name="user-edirs"),
    path("popular_edirs/", views.get_popular_edirs, name="popular-edirs"),
    path("requested_edirs/", views.get_requested_edirs, name="requested-edirs"),
    path('join_edir/<int:edir_id>/', views.join_edir, name='join-edir'), 
    path('edir_cancel_request/<int:id>/', views.cancel_edir_request, name='cancel-edir-request'),
    path('edir_leave/<int:edir_id>/', views.leave_edir, name='leave-edir'),
    path('edir_disable/<int:edir_id>/', views.disable_edir, name='disable-edir'),

    path("edir/<int:edir_id>/", views.edir_header, name="edir-detail"),
    path("edir/detail/<int:edir_id>/", views.edir_detail, name="edir-detail"),
    path("edir/update/<int:edir_id>/", views.update_edir, name="update-edir"),
    path("edir/approve/<int:id>/", views.approve_edir, name="approve_edir_edit"),
    path("edir/reject/<int:id>/", views.reject_edir, name="reject_edir_edit"),
    path("edir/cancel/<int:id>/", views.cancel_edir, name="cancel-edir"),
    path("edir/<int:pk>/update_meeting/", views.update_meeting_date, name="update-meeting-date"),

    #Bank account related endpoints
    path('add-bank/<int:edir_id>/', views.add_bank, name='add-bank'),   
    path('active_bank_list/<int:edir_id>/', views.edir_active_bank_list, name='active-bank-list'), 
    path('bank/<int:bank_id>/', views.bank_detail, name='bank-detail'), 
    path('bank/transactions/<int:bank_id>/', views.get_bank_transactions, name='bank-transactions'),
    path('update_bank/<int:bank_id>/', views.update_bank, name='update-bank'), 
    path("bank/<int:bank_id>/deactivate/", views.deactivate_bank, name="deactivate-bank"),
    path('approve_bank/<int:id>/', views.approve_bank, name='approve-bank'),
    path('reject_bank/<int:id>/', views.reject_bank, name='reject-bank'),
    path("bank/cancel/<int:id>/", views.cancel_bank, name="cancel-bank"),

    #Expense related endpoint
    path("edir/expenses/<int:edir_id>/", views.get_edir_expenses, name="get-expenses"),
    path("expense_requests/<int:edir_id>/", views.get_edir_expense_requests, name="get-edir-expense_requests"),
    path("expense/detail/<int:fee_id>/", views.get_expense_detail, name="get-expense-detail"),
    path("add_expense/<int:edir_id>/", views.add_expense, name="add-expense"),
    path("expense/update/<int:fee_id>/", views.update_expense, name="update-expense"),
    path("expense_disable/<int:fee_id>/", views.disable_expense, name="disable-expense"),
    path('approve_expense/<int:id>/', views.approve_expense, name='approve-expense'),
    path('reject_expense/<int:id>/', views.reject_expense, name='reject-expense'),
    path('expense/cancel/<int:id>/', views.cancel_expense, name='cancel-expense'),

    #Income related endpoints
    path("edir/incomes/<int:edir_id>/", views.get_edir_incomes, name="get-deposits-with-transactions"),
    path("edir/income_requests/<int:edir_id>/", views.get_income_requests_and_undeposited, name="get-income-requests-undeposited"),
    path("income/detail/<int:fee_id>/", views.get_income_detail, name="get-income-detail"),
    path("add_income/<int:edir_id>/", views.add_income, name="add-income"),
    path("income/update/<int:fee_id>/", views.update_income, name="update-income"),
    path("income_disable/<int:fee_id>/", views.disable_income, name="disable-income"),
    path('approve_income/<int:id>/', views.approve_income, name='approve-income'),
    path('reject_income/<int:id>/', views.reject_income, name='reject-income'),
    path('income/cancel/<int:id>/', views.cancel_income, name='cancel-income'),

    #Fee related endpoints
    path("fees/<int:edir_id>/", views.get_edir_fees, name="get-edir-fees"),
    path("fee_requests/<int:edir_id>/", views.get_edir_fee_requests, name="get-edir-fee_requests"),
    path("fee/detail/<int:fee_id>/", views.get_fee_detail, name="get-fee-detail"),
    path("fee/create/<int:edir_id>/", views.create_fee, name="create-fees"),
    path("fee/update/<int:fee_id>/", views.update_fee, name="update-fees"),
    path("fee_disable/<int:fee_id>/", views.disable_fee, name="disable-fee"),
    path('approve_fee/<int:id>/', views.approve_fee, name='approve-fee'),
    path('reject_fee/<int:id>/', views.reject_fee, name='reject-fee'),
    path('fee/cancel/<int:id>/', views.cancel_fee, name='cancel-fee'),
    path("fee_request/detail/<int:id>/", views.get_fee_request_detail, name="get-fee-request-detail"),

    #Payment related endpoints
    path("user/payments/<int:user_id>/", views.get_user_payments, name="get_user_payments"), #paymnet list
    path("user/payment_requests/<int:user_id>/", views.get_user_payment_requests, name="get_user_payment_requests"), #payment request list
    path("payment_details/<str:ref>/", views.get_payment_detail, name="get_payment_detail"), #payment detial
    path("transaction_details/<int:id>/", views.get_deposit_detail, name="get_transaction_detail"),
    path("fees/unpaid/<int:user_id>/", views.get_unpaid_fees, name="get_unpaid_fees"), #unpaid list for add and update paymnet
    path("fees/unpaid/paginated/<int:user_id>/", views.get_unpaid_fees_paginated, name="get_unpaid_fees_paginated"),
    path("fees/paid/<str:ref>/", views.get_paid_fees, name="get_paid_fees"), 
    path("trx/undeposited/<int:edir_id>/", views.get_undeposited_trxs, name="get-undeposited-trxs"),
    path("deposit/cashes/<int:edir_id>/", views.deposit_payments, name="deposit-cashs"),

    path("admin_pay/fees/<int:edir_id>/", views.admin_receive_cashes, name="admin-pay-fees"), #cash
    path("pay/fees/<int:edir_id>/", views.make_transfer, name="pay-fees"),#Transfer
    path("update_pay/fees/<int:edir_id>/", views.update_pay_fees, name="update-pay-fees"), #update payment
    path("disable_payment/<str:ref>/", views.disable_payment, name="disable-payment"),
    path("payment/approve/<int:id>/", views.approve_payments, name="approve-payments"),
    path("payment/reject/<int:id>/", views.reject_payment, name="reject-payments"),
    path("payment/cancel/<int:id>/", views.cancel_payment, name="cancel-payments"),
    
    #Event related endpoints
    path('add-event/<int:edir_id>/', views.add_event, name='add-event'),
    path('event_list/<int:edir_id>/', views.edir_event_list, name='event-list'),
    path('popular_event/', views.popular_event_list, name='popular-event'),
    path('event/<int:event_id>/', views.event_detail, name='event-detail'), 
    path("event/<int:event_id>/deactivate/", views.deactivate_event, name="deactivate-event"),
    
    path("help/", views.get_helps, name="user-helps"),
    path("notifications/<int:user_id>/",views.get_notifications,name="notifications"),
    path("notifications/unread/<int:user_id>/",views.get_unread_notifications,name="unread_notifications"),
    path("notifications/unread-count/<int:user_id>/",views.unread_count,name="unread-count"),
    # path("notifications/save-device-token/",views.save_device_token, name="save-device-token"),
    path("notification/<int:id>/",views.read_notification, name="read-notification"),
    path("notifications/read-all/<int:user_id>/",views.mark_all_as_read,name="mark-all-as-read"),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)