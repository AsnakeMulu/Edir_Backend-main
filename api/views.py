from django.shortcuts import render
from django.db.models import Count, Prefetch, Sum, F, OuterRef, Subquery, Exists, Q
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes, authentication_classes, parser_classes
from .serializers import EdirUserDetailSerializer, ExpenseChangeRequestSerializer, FeeChangeRequestSerializer, FamilyWithUserSerializer, EdirSerializer, IncomeDetailSerializer, PaymentChangeRequestSerializer, PaymentHistorySerializer, PaymentSerializer, TransactionSerializer, EdirSerializer, FeeSerializer, ChangePasswordSerializer, BankChangeRequestSerializer, EdirUserChangeRequestSerializer, UndepositedTransactionSerializer
from .serializers import BankWithEdirSerializer, EdirDetailSerializer, EdirSerializer, HelpSerializer, EventSerializer, FeeDetailSerializer, FeeAssignmentSerializer, EdirChangeRequestSerializer, ExpenseChangeRequestSerializer, ExpenseDetailSerializer, FamilyChangeRequestSerializer, SimpleDepositSerializer, EdirDetailOnDashboardSerializer, SimpleEdirUserSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Deposit, DepositChangeRequest, EdirChangeRequest, EdirUserChangeRequest, ExpenseChangeRequest, FeeAssignmentTrxChangeRequest, FeeChangeRequest, Family, Edir, Fee, FeeAssignment, Bank, EdirUser, Help, Event, IncomeChangeRequest, Transaction, BankChangeRequest, TransactionChangeRequest, UserChangeRequest, FamilyChangeRequest
from .pagination import AmbaPagination
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import traceback
import uuid
import json
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import MultiPartParser, FormParser
from django.forms.models import model_to_dict
from core.audit import model_to_json, audit_log
from django.core.serializers.json import DjangoJSONEncoder

User = get_user_model()

# Members
@api_view(['GET'])
@permission_classes([IsAuthenticated])  
def members_list(request, edir_id=None):
    try:
        edir = Edir.objects.get(id=edir_id)
        
        edir_users = EdirUser.objects.filter(
            edir=edir,
            status="Active"
        )
        # serializer = SimpleEdirUserSerializer(edir_users, many=True)
        paginator = AmbaPagination()
        page = paginator.paginate_queryset(edir_users, request)
        serializer = SimpleEdirUserSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)
        # return Response(serializer.data, status=status.HTTP_200_OK) 

    except Edir.DoesNotExist:
        return Response({"error": "Edir not found"}, status=status.HTTP_404_NOT_FOUND)
    except EdirUser.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="FETCH_MEMBER_LISTS",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"edir_id": edir_id, "error": str(e), "traceback":traceback.format_exc()}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])  
def member_requests(request, edir_id=None):
    try:
        edir = Edir.objects.get(id=edir_id)
        
        userRequest = EdirUserChangeRequest.objects.filter(edir=edir, status="PENDING")
        serializer = EdirUserChangeRequestSerializer(userRequest, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK) 

    except Edir.DoesNotExist:
        return Response({"error": "Edir not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="FETCH_MEMBER_LISTS",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"edir_id": edir_id, "error": str(e), "traceback":traceback.format_exc()}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # or your custom permission
def active_members_list(request, edir_id=None):
    try:
        edir = Edir.objects.get(id=edir_id)
        edir_users = EdirUser.objects.filter(
            edir=edir,
            status="Active"
        )

        serializer = EdirUserDetailSerializer(edir_users, many=True, context={"edir_id": edir.id})
        return Response(serializer.data, status=status.HTTP_200_OK) 
    except Edir.DoesNotExist:
        return Response({"error": "Edir not found"}, status=status.HTTP_404_NOT_FOUND)
    except EdirUser.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="FETCH_ACTIVE_MEMBER_LISTS",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir_id, "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# change password and user context
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail(request, user_id, edir_id=None):
    edir= None
    try:
        user = User.objects.get(id=user_id)
        membership = None
        if edir_id is not None:
            edir = Edir.objects.get(id=edir_id)
            membership = EdirUser.objects.filter(user=user, edir=edir).first()
        else:
            membership = EdirUser.objects.filter(user=user).first()

        serializer = EdirUserDetailSerializer(membership)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    except Edir.DoesNotExist:
        return Response({"error": "Edir not found"}, status=status.HTTP_404_NOT_FOUND)
    except EdirUser.DoesNotExist:
        return Response({"error": "EdirUser not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="MEMBER_DETAIL",
            request=request,
            status="FAILED",
            extra_data={"user_id": user_id,
                        "edir_id": edir_id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# Member detail
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def member_details(request, user_id):
    try:
        membership = EdirUser.objects.get(id=user_id)
        serializer = EdirUserDetailSerializer(membership)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except EdirUser.DoesNotExist:
        return Response({"error": "EdirUser not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="MEMBER_DETAILS",
            request=request,
            status="FAILED",
            extra_data={"user_id": user_id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_member(request, member_id):
    try:
        member = EdirUser.objects.select_related("edir").get(id=member_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=member.edir,
            status="Active"
        ).first()
        EdirUserChangeRequest.objects.create(
            edir_user=member,
            edir=member.edir,
            action="UPDATE",
            old_value= model_to_json(member, exclude=["updated_date"]), 
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        audit_log(
            action="UPDATE_MEMBER_REQUEST",
            request=request,
            status="SUCCESS",
            request_data= request.data,
            extra_data={
                "user_id": member_id,
                "maker": maker,
            },
        )
        return Response({"message": "Update member request sent for approval successfully"}, status=status.HTTP_201_CREATED)
    except EdirUser.DoesNotExist:
        return Response({"error": "Member not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="UPDATE_MEMBER_REQUEST",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"user_id": member_id,
                        "maker_user_id": request.user.id,
                        "error": str(e),
                        "traceback": traceback.format_exc()}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def self_register(request):
    try:
        log_data = request.data.copy()
        log_data.pop("password", None)
        log_data.pop("re_password", None)
        data = request.data  

        full_name = data.get('full_name')
        phone_number = data.get('phone_number')
        address = data.get('address')
        password = data.get('password')

        if not full_name or not phone_number:
            return Response({'error': 'full_name and phone_number are required'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create(
            phone_number=phone_number,
            password=make_password(password),
        )
        user.save()
        UserChangeRequest.objects.create(
            user=user,
            action="CREATE",
            new_value=model_to_dict(user, exclude=["password","last_login", "user_permissions","updated_date"]),
            maker=user,
            status="CREATED",
        )
        edir_user = EdirUser.objects.create(
            user=user,
            phone_number = phone_number,
            full_name=full_name,
            address=address,
            # joined_date=timezone.now(),
        )
        audit_log(
            action="SELF_REGISTRATION",
            request=request,
            status="SUCCESS",
            extra_data={
                "phone_number": phone_number,
                "full_name": full_name,
            },
        )
        return Response({'message': 'Registration successful'})
    except Exception as e:
        audit_log(
            action="SELF_REGISTRATION",
            request=request,
            status="FAILED",
            extra_data={"phone_number": phone_number,
                        "full_name": full_name,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def admin_create_user(request, edir_id):
    try:
        data = request.data  

        full_name = data.get('full_name')
        phone_number = data.get('phone_number')
        gender = data.get('gender')
        marital_status = data.get('marital_status')
        profession = data.get('profession')
        address = data.get('address')
        is_committee = data.get('is_committee', False)

        if not full_name or not phone_number:
            return Response({'error': 'full_name and phone_number are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        edir = Edir.objects.get(id=edir_id)

        #check if the edir have two committee
        committee_count = EdirUser.objects.filter(
            edir=edir,
            is_committee=True,
            status='Active'
        ).count()
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        if committee_count < 2:
            if not is_committee:  # user is not committee
                return Response(
                    {"error": "First add the second committee before add members"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                # allow direct save (committee user)
                is_user_exist = User.objects.filter(phone_number=phone_number).exists()
                if not is_user_exist:
                    user = User.objects.create(
                        phone_number=phone_number,
                    )
                    user.set_unusable_password()
                    user.save()
                    UserChangeRequest.objects.create(
                        user=user,
                        action="CREATE",
                        new_value=request.data,
                        maker=request.user,
                        status="CREATED",
                    )
                
                user = User.objects.filter(phone_number=phone_number).first()
                edir_user = EdirUser.objects.create(
                    user=user,
                    edir=edir,
                    phone_number= phone_number,
                    full_name=full_name,
                    gender=gender,
                    marital_status=marital_status,
                    profession=profession,
                    address=address,
                    is_committee=bool(is_committee),
                    joined_date=timezone.now(),
                )
                EdirUserChangeRequest.objects.create(
                    edir_user=edir_user,
                    edir=edir,
                    action="CREATE",
                    new_value=request.data,
                    maker=maker,
                    status="CREATED",
                )
                audit_log(
                    action="ADD_COMMITTEE_MEMBER",
                    request=request,
                    status="SUCCESS",
                    extra_data={
                        "phone_number": phone_number,
                        "full_name": full_name,
                        "edir_id": edir_id
                    },
                )
            return Response({'message': 'Committee member added by admin successfully'}, status=status.HTTP_201_CREATED)
        else:
            EdirUserChangeRequest.objects.create(
                edir=edir,
                action="CREATE",
                new_value=request.data,
                phone_number= phone_number,
                status="PENDING",
                maker=maker,
            )
            audit_log(
                action="CREATE_MEMBER_REQUEST",
                request=request,
                status="SUCCESS",
                extra_data={
                    "phone_number": phone_number,
                    "full_name": full_name,
                    "edir_id": edir_id
                },
            )
            return Response(
                {"message": "Request sent for approval"},
                status=status.HTTP_201_CREATED
            )

    except Edir.DoesNotExist:
        return Response({'error': 'Edir not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="CREATE_MEMBER_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir_id, 
                        "maker": maker.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def approve_member (request, id):
    try:
        change = EdirUserChangeRequest.objects.get(id=id)
        edir = change.edir
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = change.new_value
        edir_user=change.edir_user
        
        full_name = data.get('full_name')
        phone_number = data.get('phone_number')
        gender = data.get('gender')
        marital_status = data.get('marital_status')
        profession = data.get('profession')
        address = data.get('address')
        is_committee = data.get('is_committee', False)
        
        if change.action == "CREATE":
            is_user_exist = User.objects.filter(phone_number=phone_number).exists()
            if not is_user_exist:
                user = User.objects.create(
                    phone_number=phone_number,
                )
                user.set_unusable_password()
                user.save()
            edir_user = None
            user = User.objects.filter(phone_number=phone_number).first()
            is_user_has_no_edir = EdirUser.objects.filter(Q(user=user, edir__isnull=True)).exists()
            if is_user_has_no_edir:
                edir_user = EdirUser.objects.filter(Q(user=user, edir__isnull=True)).first()
                edir_user.edir = edir
                edir_user.full_name = full_name
                edir_user.gender=gender
                edir_user.marital_status=marital_status
                edir_user.profession=profession
                edir_user.address=address
                edir_user.is_committee=bool(is_committee)
                edir_user.joined_date=timezone.now()
                edir_user.save()
            else:  
                edir_user = EdirUser.objects.create(
                    user=user,
                    edir=edir,
                    phone_number= phone_number,
                    full_name=full_name,
                    gender=gender,
                    marital_status=marital_status,
                    profession=profession,
                    address=address,
                    is_committee=bool(is_committee),
                    joined_date=timezone.now(),
                )
            
            change.edir_user = edir_user
            audit_log(
                action="APPROVE_CREATE_MEMBER",
                request=request,
                status="SUCCESS",
                extra_data={
                    "phone_number": phone_number,
                    "full_name": full_name,
                    "checker_id": checker.id
                },
            )
        elif change.action == "UPDATE":
            edir_user.phone_number = phone_number
            edir_user.full_name = full_name
            edir_user.address = address
            edir_user.gender = gender
            edir_user.marital_status = marital_status
            edir_user.profession = profession
            edir_user.is_committee = bool(is_committee)
            edir_user.updated_date=timezone.now()
            edir_user.save()
            audit_log(
                action="APPROVE_UPDATE_MEMBER",
                request=request,
                status="SUCCESS",
                extra_data={
                    "phone_number": phone_number,
                    "full_name": full_name,
                    "checker_id": checker.id
                },
            )

        elif change.action == "DISABLE":
            change.comment = data.get("reason")

            edir_user.status = "Not Active"
            edir_user.updated_date = timezone.now()
            edir_user.save()
            audit_log(
                action="APPROVE_DEACTIVATE_MEMBER",
                request=request,
                status="SUCCESS",
                extra_data={
                    "phone_number": phone_number,
                    "full_name": full_name,
                    "checker_id": checker.id
                },
            )

        change.status = "APPROVED"
        change.approved_at = timezone.now()
        change.checker = checker
        change.save()
        return JsonResponse({"message": "The request was approved successfully", }, status=200)
    except EdirUserChangeRequest.DoesNotExist:
        return JsonResponse({"error": "The change request is not found "}, status=404)
    except EdirUser.DoesNotExist:
        return JsonResponse({"error": "The checker is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="APPROVE_MEMBER_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"request_id": id,
                        "cheker_user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def reject_member (request, id):
    try:
        change = EdirUserChangeRequest.objects.get(id=id)
        reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        change.status = "Rejected"
        change.approved_at = timezone.now()
        change.checker = checker
        change.comment= reason
        change.save()      
        audit_log(
            action="REJECT_MEMBER",
            request=request,
            status="SUCCESS",
            extra_data={
                "request_id": id,
                "rejection_reason": reason,
                "checker_id": checker.id
            },
        )
        return JsonResponse({
            "message": "Member request rejected successfully",
        }, status=200)
    except EdirUserChangeRequest.DoesNotExist:
        return JsonResponse({"error": "The change request is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="REJECT_MEMBER",
            request=request,
            status="FAILED",
            extra_data={"request_id": id,
                        "cheker_user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def cancel_member (request, id):
    try:
        change = EdirUserChangeRequest.objects.get(id=id)
        # reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        change.status = "Cancelled"
        change.approved_at = timezone.now()
        change.checker = checker
        # change.comment= reason
        change.save()      
        audit_log(
            action="CANCEL_MEMBER",
            request=request,
            status="SUCCESS",
            request_data=request.data,
            extra_data={
                "request_id": id,
                "checker_id": checker.id
            },
        )
        return JsonResponse({"message": "Member request cancelled successfully"}, status=200)
    except EdirUserChangeRequest.DoesNotExist:
        return JsonResponse({"error": "The change request is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="REJECT_MEMBER",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"request_id": id,
                        "cheker_user_id": request.user.id,
                        "error": str(e),
                        "traceback":traceback.format_exc()}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_user_in_edir(request, edir_id, phone_number):
    try:
        edir = Edir.objects.get(id=edir_id) 
        user = User.objects.filter(phone_number=phone_number).first()

        if user:
            is_member = EdirUser.objects.filter(user=user, edir=edir).exists()
            if is_member:
                return Response({
                    "exists": True,
                    "message": "User is already a member of this edir"
                }, status=200)

        has_pending = EdirUserChangeRequest.objects.filter(
            phone_number=phone_number,
            edir=edir,
            status="PENDING"
        ).exists()

        if has_pending:
            return Response({
                "exists": True,
                "message": "User already has a pending request"
            }, status=200)
        
        return Response({
            "exists": False,
            "message": "User is not a member and has no pending request"
        }, status=200)
    
    except Edir.DoesNotExist:
        return Response({ "error": "Edir not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="CHECK_USER_EXIST",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir_id, 
                        "phone_number": phone_number,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# login
@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])  # allow unauthenticated users
def set_new_password(request):
    phone_number = request.data.get("phone_number")
    password = request.data.get("password")

    if not phone_number or not password:
        return Response(
            {"error": "Phone number and password are required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        user = User.objects.get(phone_number=phone_number)
        # Only allow if the user has no usable password
        if user.has_usable_password():
            return Response(
                {"error": "User already has a password. Please login instead."},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Set password
        user.set_password(password)
        user.save()
        refresh = RefreshToken.for_user(user)
        audit_log(
                action="SET_NEW_PASSWORD",
                request=request,
                status="SUCCESS",
                extra_data={
                    "phone_number": phone_number,
                    "user_id": user.id
                },
            )
        return Response({"message": "Password set successfully"}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response(
            {"error": f"Phone {phone_number} does not exist"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        audit_log(
            action="SET_NEW_PASSWORD",
            request=request,
            status="FAILED",
            extra_data={"phone_number": phone_number,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# login
@api_view(["POST"])
@permission_classes([AllowAny])  
def check_phone(request):
    phone_number = request.data.get("phone_number")
    if not phone_number:
        return Response({"error": "Phone number is required"}, status=400)

    try:
        user = User.objects.get(phone_number=phone_number)
        return Response({
            "exists": True,
            "has_password": user.has_usable_password()
        })
    except User.DoesNotExist:
        return Response(
            {"exists": False, "error": f"Phone {phone_number} not exist"},
            status=404
        )

#login and registration
@api_view(['GET'])
@permission_classes([AllowAny])
def check_user_phone(request, phone_number):
    try:
        if not phone_number:
            return Response({'error': 'Phone number is required.'}, status=status.HTTP_400_BAD_REQUEST)

        exists = User.objects.filter(phone_number=phone_number).exists()
        edir_user_exists = EdirUser.objects.filter(phone_number=phone_number).exists()
        return Response({
            "phone_number": phone_number,
            "exists": exists,
            "edir_user_exists": edir_user_exists
        }, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    except EdirUser.DoesNotExist:
        return Response({"error": "EdirUser not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="CHECK_MEMBER_PHONE",
            request=request,
            status="FAILED",
            extra_data={"phone_number": phone_number,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def deactivate_member(request, member_id):
    try:
        user = EdirUser.objects.get(id=member_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=user.edir,
            status="Active"
        ).only("id").first()
        EdirUserChangeRequest.objects.create(
            edir_user=user,
            edir=user.edir,
            action="DISABLE",
            old_value= model_to_json(user, exclude=["updated_date"]), 
            new_value= request.data,
            maker=maker,
            status="PENDING",
        )
        audit_log(
            action="DEACTIVATE_MEMBER_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "user_id": user.id,
                "maker_id": maker.id,
            },
        )
        return JsonResponse({
            "message": "Member deactivation request sent for approval successfully",
        }, status=200)

    except Edir.DoesNotExist:
        return JsonResponse({"error": "Edir not found"}, status=404)
    except EdirUser.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except Exception as e:
        audit_log(
            action="DEATIVATE_MEMBER_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"user_id": member_id,
                        "maker_user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def add_family(request, user_id):
    try:
        user = EdirUser.objects.get(id=user_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=user.edir,
            status="Active"
        ).only("id").first()

        FamilyChangeRequest.objects.create(
            edir_user=user,
            action="CREATE",
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        audit_log(
            action="ADD_FAMILY_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "maker_id":maker.id,
                "user_id": user_id
            },
        )
        return Response({'message': 'family added by admin'}, status=status.HTTP_201_CREATED)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="ADD_FAMILY_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"user_id": user_id,
                        "maker_user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_family_list(request, user_id):
    try:
        user = EdirUser.objects.get(id=user_id)
        family = Family.objects.filter(user=user, status="Active")
        # serializer = FamilyWithUserSerializer(family, many=True)
        
        paginator = AmbaPagination()
        page = paginator.paginate_queryset(family, request)
        serializer = FamilyWithUserSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)
        # return Response(serializer.data)
    except EdirUser.DoesNotExist:
        return Response({"detail": "Member not added"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="FAMILY_LIST",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"user_id": user_id,
                        "maker_user_id": request.user.id,
                        "error": str(e),
                        "traceback":traceback.format_exc()}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_family_requests(request, user_id):
    try:
        user = EdirUser.objects.get(id=user_id)
        
        family_request = FamilyChangeRequest.objects.filter(edir_user=user, status="PENDING")
        serializer = FamilyChangeRequestSerializer(family_request, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"detail": "Partner not added"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="FAMILY_LIST",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"user_id": user_id,
                        "maker_user_id": request.user.id,
                        "error": str(e),
                        "traceback":traceback.format_exc()}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def family_detail(request, family_id):
    try:
        family = Family.objects.get(id=family_id)
        if request.method == 'GET':
            serializer = FamilyWithUserSerializer(family)
            return Response(serializer.data)
        
        elif request.method in ['PUT', 'PATCH']:
            serializer = FamilyWithUserSerializer(family, data=request.data, partial=True)
            if serializer.is_valid():
                current_user = EdirUser.objects.filter(
                    user=request.user,
                    edir=family.user.edir,
                    status="Active"
                ).only("id").first()
                FamilyChangeRequest.objects.create(
                    family=family,
                    edir_user=family.user,
                    action="UPDATE",
                    old_value= model_to_json(family, exclude=["updated_date"]), 
                    new_value=request.data,
                    maker=current_user,
                    status="PENDING",
                )
                audit_log(
                    action="UPATE_FAMILY_REQUEST",
                    request=request,
                    status="SUCCESS",
                    extra_data={
                        "maker_id":current_user.id,
                        "user_id": family.user.id
                    },
                )
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Family.DoesNotExist:
        return Response({"detail": "Family not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="FAMILY_DETAIL",
            request=request,
            status="FAILED",
            extra_data={"family_id": family_id,
                        "maker_user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def deactivate_family(request, family_id):
    try:
        family = Family.objects.get(id=family_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=family.user.edir,
            status="Active"
        ).only("id").first()

        FamilyChangeRequest.objects.create(
            family=family,
            edir_user=family.user,
            action="DISABLE",
            old_value= model_to_json(family, exclude=["updated_date"]), 
            new_value= request.data,
            maker=maker,
            status="PENDING",
        )
        audit_log(
            action="DEACTIVATE_FAMILY_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "maker_id":maker.id,
                "user_id": family.user.id
            },
        )
        return JsonResponse({"message": "Family deactivated successfully",}, status=200)
    except Family.DoesNotExist:
        return JsonResponse({"error": "Family not found"}, status=404)
    except Exception as e:
        audit_log(
            action="DEACTIVATE_FAMILY_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"family_id": family_id,
                        "maker_user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def approve_family(request, id):
    try:
        change = FamilyChangeRequest.objects.get(id=id)
        edir_user = change.edir_user
        family=change.family
        data = change.new_value
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=edir_user.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        full_name = data.get('full_name')
        gender = data.get('gender')
        relationship = data.get('relationship')
        profession = data.get('profession')
        
        if change.action == "CREATE":
            family = Family.objects.create(
                user=edir_user,
                full_name=full_name,
                gender=gender,
                relationship=relationship,
                profession=profession,
                created_date=timezone.now(),
            )
            change.family = family
            audit_log(
                action="APPROVE_CREATE_FAMILY",
                request=request,
                status="SUCCESS",
                extra_data={
                    "family_id": family.id,
                    "family_request_id": id,
                    "full_name": full_name,
                    "checker_id": checker.id
                },
            )
        elif change.action == "UPDATE":

            family.full_name = full_name
            family.gender = gender
            family.relationship = relationship
            family.profession = profession
            family.save()
            audit_log(
                action="APPROVE_UPDATE_FAMILY",
                request=request,
                status="SUCCESS",
                extra_data={
                    "family_id": family.id,
                    "family_request_id": id,
                    "full_name": full_name,
                    "checker_id": checker.id
                },
            )
        elif change.action == "DISABLE":
            change.comment = data.get("reason")

            family.status = "Not Active"
            family.updated_date = timezone.now()
            family.save()
            audit_log(
                action="APPROVE_DISABLE_FAMILY",
                request=request,
                status="SUCCESS",
                extra_data={
                    "family_id": family.id,
                    "family_request_id": id,
                    "full_name": full_name,
                    "checker_id": checker.id
                },
            )
        change.status = "APPROVED"
        change.approved_at = timezone.now()
        change.checker = checker
        change.save()
        return JsonResponse({"message": "Family request approved successfully"}, status=200)
    except FamilyChangeRequest.DoesNotExist:
        return JsonResponse({"error": "Family change request is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="APPROVE_FAMILY_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"request_id": id,
                        "checker_user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def reject_family(request, id):
    try:
        change = FamilyChangeRequest.objects.get(id=id)
        reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir_user.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        change.status = "Rejected"
        change.approved_at = timezone.now()
        change.checker = checker
        change.comment= reason
        change.save()
        audit_log(
            action="REJECT_FAMILY_REQUEST",
            request=request,
            status="SUCCESS",
            request_data=request.data,
            extra_data={
                "family_request_id": id,
                "reason": reason,
                "checker_id": checker.id
            },
        )
        return JsonResponse({"message": "Family request rejected successfully",}, status=200)
    except FamilyChangeRequest.DoesNotExist:
        return JsonResponse({"error": "Family change request is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="REJECT_FAMILY",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"request_id": id,
                        "checker_user_id": request.user.id,
                        "error": str(e), 
                        "traceback":traceback.format_exc()}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def cancel_family(request, id):
    try:
        change = FamilyChangeRequest.objects.get(id=id)
        # reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir_user.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        change.status = "Cancelled"
        change.approved_at = timezone.now()
        change.checker = checker
        # change.comment= reason
        change.save()
        audit_log(
            action="CANCEL_FAMILY",
            request=request,
            status="SUCCESS",
            request_data=request.data,
            extra_data={
                "family_request_id": id,
                "checker_id": checker.id
            },
        )
        return JsonResponse({"message": "Family request cancelled successfully",}, status=200)
    except FamilyChangeRequest.DoesNotExist:
        return JsonResponse({"error": "Family change request is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="CANCEL_FAMILY",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"request_id": id,
                        "checker_user_id": request.user.id,
                        "error": str(e),
                        "traceback":traceback.format_exc()}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_edir(request):
    try:
        #Create Edir
        data = request.data
        edir_user = None
        serializer = EdirSerializer(data=data)
        if serializer.is_valid():
            edir = serializer.save() 
            maker = EdirUser.objects.filter(
                user=request.user,
                edir=edir,
                status="Active"
            ).only("id").first()
            edir_request = EdirChangeRequest.objects.create(
                edir=edir,
                action="CREATE",
                new_value=data,
                maker=maker,
                status="CREATED",
            )
            audit_log(
                action="CREATE_EDIR",
                request=request,
                status="SUCCESS",
                extra_data={
                    "edir_id": edir.id,
                    "request_id": edir_request.id,
                    "maker_user_id": request.user.id
                },
            )
            has_no_edir = EdirUser.objects.filter(user=request.user, edir__isnull=True).exists()
            if has_no_edir:
                edir_user = EdirUser.objects.filter(user=request.user, edir__isnull=True).first()     
                edir_user.edir = edir
                edir_user.is_committee=True
                edir_user.joined_date = timezone.now()
                edir_user.save()
                audit_log(
                    action="ADD_EDIR_CREATOR",
                    request=request,
                    status="SUCCESS",
                    extra_data={
                        "edir_id": edir.id,
                        "user_id": edir_user.id
                    },
                )
            else:
                # Add creator as committee member of the Edir
                id = request.data.get('id')
                current_user = None
                if id is not None:
                    current_user = EdirUser.objects.filter(user=request.user, edir_id = id).first()
                else:
                    current_user = EdirUser.objects.filter(user=request.user).first()
                edir_user = EdirUser.objects.create(
                    user=request.user,
                    edir=edir,
                    phone_number = current_user.phone_number,
                    full_name=current_user.full_name,
                    address = current_user.address,
                    gender = current_user.gender,
                    marital_status = current_user.marital_status,
                    profession= current_user.profession,
                    image =current_user.image,
                    is_committee=True,
                    status="Active",
                    joined_date=timezone.now()
                )
                audit_log(
                    action="ADD_EDIR_CREATOR",
                    request=request,
                    status="SUCCESS",
                    extra_data={
                        "edir_id": edir.id,
                        "user_id": edir_user.id
                    },
                )
            EdirUserChangeRequest.objects.create(
                edir_user=edir_user,
                action="ADD_MEMBER",
                maker=maker,
                new_value=model_to_json(edir_user),
                status="CREATED", 
            )
            return Response({'message':'Edir created successfully'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': 'Bad request error', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        audit_log(
            action="CREATE_EDIR",
            request=request,
            status="FAILED",
            extra_data={"user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# Dashboard
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_with_edirs(request):
    id = request.query_params.get('id')
    edirSerializer = None
    eventSerializer = None
    edir = None
    try:
        if id is not None:
            is_user_has_edir = EdirUser.objects.filter(
                edir_id=id,
                user=request.user,
                status="Active"
            ).exists()

            if is_user_has_edir:
                edir = Edir.objects.filter(id=id).first()

        if edir is None:
            edir = Edir.objects.filter(
                ediruser__user=request.user,
                ediruser__status="Active"
            ).first()

        if edir is not None:
            current_user = EdirUser.objects.filter(
                user=request.user,
                edir=edir,
                status="Active"
            ).only("id").first()
            
            edirSerializer = EdirDetailOnDashboardSerializer(edir, context={"request": request})
            
            event = Event.objects.filter(edir=edir, status="Active").order_by("-created_date")[:3]
            eventSerializer = EventSerializer(event, many=True)
            
            payments = (
                Transaction.objects.filter(
                    user=current_user,
                    # edir=edir,
                    payment_status__in=["Paid", "PAID"]
                )
                .prefetch_related(
                    Prefetch(
                        "feeassignment_trx",
                        queryset=FeeAssignment.objects.select_related(
                            "fee",
                            "fee__supported_member",
                        )
                    )
                ).order_by("-created_at")
            )[:5]
            serializer = PaymentSerializer(payments, many=True)  
            return Response({"edir": edirSerializer.data, "events": eventSerializer.data, "payments": serializer.data, "has_edir":True})
        else:
            return Response({"edir": None, "events": None, "payments":None, "has_edir":False})
    except Edir.DoesNotExist:
        return Response({"error": "Edir is not found "}, status=404)
    except EdirUser.DoesNotExist:
        return Response({"error": "Edir User is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="DASHBOARD",
            request=request,
            status="FAILED",
            extra_data={"user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_edirs(request):
    try:
        edirs = Edir.objects.filter(
            ediruser__user=request.user,
            ediruser__status="Active", 
            status="Active"  
        )
        serializer = EdirSerializer(edirs, many=True)
        return Response(serializer.data)
    except Edir.DoesNotExist:
        return Response({"error": "Edir  is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="FETCH_USER_EDIRS",
            request=request,
            status="FAILED",
            extra_data={"user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_popular_edirs(request):
    try:
        excluded_edirs = EdirUser.objects.filter(
            user=request.user,
            status="Active"
        ).values("edir_id")
        excluded_edir_requests = EdirUserChangeRequest.objects.filter(
            user=request.user.phone_number,
            status="PENDING"
        ).values("edir_id")

        edirs = Edir.objects.filter(
            status="Active", is_popular = True
        ).exclude(
            id__in=Subquery(excluded_edirs, excluded_edir_requests)
        )

        serializer = EdirSerializer(edirs, many=True)
        return Response(serializer.data)
    except Edir.DoesNotExist:
        return Response({"error": "Edir  is not found "}, status=404)
    except EdirUser.DoesNotExist:
        return Response({"error": "Edir User is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="FETCH_POPULAR_EDIRS",
            request=request,
            status="FAILED",
            extra_data={"user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_requested_edirs(request):
    try:
        edirs = EdirUserChangeRequest.objects.filter(
            user=request.user.phone_number,
            status__in=["PENDING", "REJECTED", "CANCELLED"],
            action = "JOIN_REQUEST"
        )

        serializer = EdirUserChangeRequestSerializer(edirs, many=True)
        return Response(serializer.data)
    except EdirUserChangeRequest.DoesNotExist:
        return Response({"error": "Edir User change request is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="FETCH_POPULAR_EDIRS",
            request=request,
            status="FAILED",
            extra_data={"user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_edir(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
        # user = User.objects.get(id =request.user.id)
        edir_user = EdirUser.objects.filter(user=request.user).last()
        EdirUserChangeRequest.objects.create(
            phone_number=edir_user.phone_number,
            edir=edir,
            action="JOIN", 
            new_value=model_to_json(edir_user, exclude=["updated_date"]),
            # maker=maker,
            status="PENDING",
        )
        return Response({'message': 'Edir join request submitted successfully'}, status=status.HTTP_201_CREATED)
    except Edir.DoesNotExist:
        return Response({'error': 'Edir not found'}, status=status.HTTP_404_NOT_FOUND)
    except EdirUser.DoesNotExist:
        return JsonResponse({"error": "Edir User is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="JOIN_EDIR_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir.id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def cancel_edir_request (request, id):
    try:
        change = BankChangeRequest.objects.get(id=id)
        reason = request.data.get('reason')
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        change.status = "CANCELLED"
        change.approved_at = timezone.now()
        change.comment= reason
        change.save()

        return JsonResponse({"message": "Edir request cancelled successfully"}, status=200)
    except Edir.DoesNotExist:
        return JsonResponse({"error": "Edir is not found "}, status=404)
    except EdirUser.DoesNotExist:
        return JsonResponse({"error": "User is not found in Edir Request"}, status=404)
    except Exception as e:
        audit_log(
            action="CANCEL_EDIR_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"request_id": id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def leave_edir (request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
        edir_user = EdirUser.objects.get(edir=edir, user=request.user)
        reason = request.data.get('reason')

        edir_user.status = "Leaved"
        edir_user.leave_reason = reason
        edir_user.updated_date = timezone.now()
        edir_user.save()
        
        audit_log(
            action="LEAVE_EDIR",
            request=request,
            status="SUCCESS",
            extra_data={
                "edir_id":edir.id,
                "user_id": edir_user.id
            },
        )
        return JsonResponse({"message": "You have left the Edir successfully"}, status=200)
    except Edir.DoesNotExist:
        return JsonResponse({"error": "Edir is not found "}, status=404)
    except EdirUser.DoesNotExist:
        return JsonResponse({"error": "User is not found in Edir Request"}, status=404)
    except Exception as e:
        audit_log(
            action="LEAVE_EDIR",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir.id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def disable_edir(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
        edir_user = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).first()
        EdirChangeRequest.objects.create(
            edir=edir,
            action="DISABLE",
            old_value= model_to_json(edir, exclude=["updated_date", "users"]), 
            new_value= request.data,
            maker=edir_user,
            status="PENDING",
        )
        audit_log(
            action="DISABLE_EDIR_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "edir_id":edir.id,
                "user_id": edir_user.id
            },
        )
        return JsonResponse({"message": "Edir deactivation request recorded successfully"}, status=200)
    except Edir.DoesNotExist:
        return Response({"error": "Edir not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="DISABLE_EDIR_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir.id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def edir_header(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
        serializer = EdirDetailSerializer(edir)
        return Response(serializer.data)
    except Edir.DoesNotExist:
        return Response({"error": "Edir not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="FETCH_HEADER_EDIR",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir.id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def edir_detail(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
        edirSerializer = EdirSerializer(edir)
        
        bank = Bank.objects.filter(edir=edir, status="Active")
        bankSerializer = BankWithEdirSerializer(bank, many=True)

        changeRequest = EdirChangeRequest.objects.filter(edir=edir, status="PENDING")
        changeRequestSerializer = EdirChangeRequestSerializer(changeRequest, many=True)

        bankRequest = BankChangeRequest.objects.filter(edir=edir, status="PENDING")
        bankRequestSerializer = BankChangeRequestSerializer(bankRequest, many=True)
        return Response({"edir": edirSerializer.data, 
                         "banks": bankSerializer.data, 
                         "change_requests": changeRequestSerializer.data, 
                         "bank_change_requests": bankRequestSerializer.data})
    except Edir.DoesNotExist:
        return Response({"error": "Edir is not found."},status=status.HTTP_404_NOT_FOUND)
    except Bank.DoesNotExist:
        return Response({"error": "Bank is not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="EDIR_DETAILS",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_edir(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        EdirChangeRequest.objects.create(
            edir=edir,
            action="UPDATE",
            old_value= model_to_json(edir, exclude=["updated_date", "users"]), 
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        audit_log(
            action="UPDATE_EDIR_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "edir_id":edir.id,
                "maker_user_id": maker.id
            },
        )
        return Response("Message: Update request submitted successfully.", status=status.HTTP_200_OK)
    except Edir.DoesNotExist:
        return Response({"error": "Edir not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="UPDATE_EDIR_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def approve_edir(request, id):
    try:
        change = EdirChangeRequest.objects.get(id=id)
        edir = change.edir
        new = change.new_value
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if change.action == "UPDATE":
            edir.name = new.get("name")
            edir.monthly_fee = new.get("monthly_fee")
            edir.address = new.get("address")
            edir.description = new.get("description")
            edir.updated_date = timezone.now()

            edir.save()
            audit_log(
                action="APPROVE_UPDATE_EDIR",
                request=request,
                status="SUCCESS",
                extra_data={
                    "edir_id": edir.id,
                    "checker_user_id": checker.id
                }
            )
        elif change.action == "DISABLE":
            edir.status = "Not Active"
            edir.updated_date = timezone.now()
            edir.save()
            audit_log(
                action="APPROVE_DISABLE_EDIR",
                request=request,
                status="SUCCESS",
                extra_data={
                    "edir_id": edir.id,
                    "checker_user_id": checker.id
                }
            )
            change.comment = new.get("reason")
        change.status = "APPROVED"
        change.checker = checker
        change.approved_at = timezone.now()
        change.save()
        return Response({"message": "Approved successfully"}, status=status.HTTP_200_OK)
    except EdirChangeRequest.DoesNotExist:
        return Response({"error": "Change request not found"},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="UPDATE_EDIR_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"request_id": id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def reject_edir(request, id):
    try:
        change = EdirChangeRequest.objects.get(id=id)
        reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        edir = change.edir
        change.status = "REJECTED"
        change.checker = checker
        change.comment = reason
        change.approved_at = timezone.now()
        change.save()
        audit_log(
            action="REJECT_EDIR",
            request=request,
            status="SUCCESS",
            extra_data={
                "request_id": id,
                "checker_user_id": checker.id
            }
        )
        return Response({"message": "Rejected successfully"},status=status.HTTP_200_OK)
    except EdirChangeRequest.DoesNotExist:
        return Response({"error": "Change request not found"},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="REJECT_EDIR_REQUEST",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"request_id": id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def cancel_edir(request, id):
    try:
        change = EdirChangeRequest.objects.get(id=id)
        # reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        edir = change.edir
        change.status = "CANCELLED"
        change.checker = checker
        # change.comment = reason
        change.approved_at = timezone.now()
        change.save()
        audit_log(
            action="CANCEL_EDIR",
            request=request,
            status="SUCCESS",
            request_data=request.data,
            extra_data={
                "request_id": id,
                "checker_user_id": checker.id
            }
        )
        return Response(
            {"message": "Edir request Cancelled successfully"},status=status.HTTP_200_OK)
    except EdirChangeRequest.DoesNotExist:
        return Response({"error": "Change request not found"},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="CANCEL_EDIR_REQUEST",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"request_id": id,
                        "user_id": request.user.id,
                        "error": str(e),
                        "traceback": traceback.format_exc()
                        }
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_meeting_date(request, pk):
    try:
        edir = Edir.objects.get(id=pk)
        edir.meeting_date = request.data.get("meeting_date")
        edir.meeting_place = request.data.get("meeting_place")
        edir.save()
        audit_log(
            action="UPDATE_MEETING_DATE",
            request=request,
            status="SUCCESS",
            extra_data={
                "edir_id": pk,
                "user_id": request.user.id
            }
        )
        return Response({"message": "Meeting date updated"}, status=200)
    except Edir.DoesNotExist:
        return Response({"error": "Edir not found"}, status=404)
    except Exception as e:
        audit_log(
            action="UPDATE_MEETING_DATE",
            request=request,
            status="FAILED",
            extra_data={"edir_id": pk,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def add_bank(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        bank_request = BankChangeRequest.objects.create(
            edir=edir,
            action="CREATE",
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        audit_log(
            action="ADD_BANK_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "edir_id": edir_id,
                "request_id": bank_request.id,
                "maker_id": maker.id
            },
        )
        return Response({'message': 'bank added by admin'}, status=status.HTTP_201_CREATED)

    except Edir.DoesNotExist:
        return Response({'error': 'edir not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="ADD_BANK_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir_id,
                        "maker_user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def edir_active_bank_list(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
        bank = Bank.objects.filter(edir=edir, status="Active")
        
        serializer = BankWithEdirSerializer(bank, many=True)
        return Response(serializer.data)
    except Exception as e:
        audit_log(
            action="FETCH_BANK_LISTS",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir_id,
                        "fetcher_user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_bank_transactions(request, bank_id):
    try:
        bank = Bank.objects.get(id=bank_id)
        
        deposits = (
            Deposit.objects
            .filter(bank=bank, payment_status__in=["Paid", "PAID"])
            .annotate(total_amount=Sum("transactions__amount"))
            .order_by("-created_at")
        )
        paginator = AmbaPagination()
        page = paginator.paginate_queryset(deposits, request)
        serializer = SimpleDepositSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)
        # serializer = SimpleDepositSerializer(deposits, many=True)
        # return Response(serializer.data, status=200)
    except Bank.DoesNotExist:
        return Response({'error': 'Bank not found'},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="FETCH_BANK_TRANSACTIONS",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"bank_id": bank_id,
                        "fetcher_user_id": request.user.id,
                        "error": str(e),
                        "traceback":traceback.format_exc()}
        )
        return Response(
            {'error': 'Bank not found or failed to fetch bank transactions'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bank_detail(request, bank_id):
    try:
        bank = Bank.objects.get(id=bank_id)
        serializer = BankWithEdirSerializer(bank)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Bank.DoesNotExist:
        return Response({"detail": "Bank not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="BANK_DETAIL",
            request=request,
            status="FAILED",
            extra_data={"bank_id": bank_id,
                        "fetcher_user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'failed to fetch bank details'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_bank(request, bank_id):
    try:
        bank = Bank.objects.get(id=bank_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=bank.edir,
            status="Active"
        ).only("id").first()
        BankChangeRequest.objects.create(
            bank=bank,
            edir=bank.edir,
            action="UPDATE",
            old_value= model_to_json(bank, exclude=["updated_date"]), 
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        serializer = BankWithEdirSerializer(bank)
        audit_log(
            action="UPDATE_BANK_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "maker_id":maker.id,
                "bank_id": bank.id
            },
        )
        return Response({"message": "Bank update request recorded successfully"}, status=status.HTTP_200_OK)
    except Bank.DoesNotExist:
        return Response({"error": "Bank not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="UPDATE_BANK_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"bank_id": bank_id,
                        "maker_user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def deactivate_bank(request, bank_id):
    try:
        bank = Bank.objects.get(id=bank_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=bank.edir,
            status="Active"
        ).only("id").first()
        BankChangeRequest.objects.create(
            bank=bank,
            edir=bank.edir,
            action="DISABLE",
            old_value= model_to_json(bank, exclude=["updated_date"]), 
            new_value= request.data,
            maker=maker,
            status="PENDING",
        )
        audit_log(
            action="DEACTIVATE_BANK_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "maker_id":maker.id,
                "bank_id": bank.id
            },
        )
        return JsonResponse({"message": "Bank deactivation request recorded successfully"}, status=200)
    except Bank.DoesNotExist:
        return Response({"error": "Bank not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="DEACTIVATE_BANK_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"bank_id": bank.id,
                        "maker_user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def approve_bank (request, id):
    try:
        change = BankChangeRequest.objects.get(id=id)
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        edir = change.edir
        new = change.new_value
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()

        account_name = new.get("account_name")
        account_number = new.get("account_number")
        bank_name = new.get("bank_name")
        if change.action == "CREATE":
            bank = Bank.objects.create(
                edir = edir,
                account_name=account_name,
                bank_name=bank_name,
                account_number=account_number,
                status = "Active", 
                created_date=timezone.now()
            )
            bank.save()
            change.bank = bank
            audit_log(
                action="APPROVE_CREATE_BANK",
                request=request,
                status="SUCCESS",
                extra_data={
                    "bank_id": bank.id,
                    "bank_request_id": id,
                    "checker_id": checker.id
                },
            )
        elif change.action == "UPDATE":
            bank = change.bank
            bank.account_name = account_name
            bank.account_number = account_number
            bank.bank_name = bank_name
            bank.updated_date = timezone.now()
            bank.save()
            audit_log(
                action="APPROVE_UPDATE_BANK",
                request=request,
                status="SUCCESS",
                extra_data={
                    "bank_id": bank.id,
                    "bank_request_id": id,
                    "checker_id": checker.id
                },
            )
        elif change.action == "DISABLE":
             bank = change.bank
             bank.status = "Not Active"
             bank.updated_date = timezone.now()
             bank.save()
             audit_log(
                action="APPROVE_DISABLE_BANK",
                request=request,
                status="SUCCESS",
                extra_data={
                    "bank_id": bank.id,
                    "bank_request_id": id,
                    "checker_id": checker.id
                },
            )
        change.status = "APPROVED"
        change.approved_at = timezone.now()
        change.checker = checker
        change.save()
        return JsonResponse({"message": "Bank request aproved successfully"}, status=200)
    except BankChangeRequest.DoesNotExist:
        return JsonResponse({"error": "Bank is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="APPROVE_BANK_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"request_id": id,
                        "checker_user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def reject_bank (request, id):
    try:
        change = BankChangeRequest.objects.get(id=id)
        reason = request.data.get('reason')
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        edir = change.edir
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()

        change.status = "Rejected"
        change.approved_at = timezone.now()
        change.checker = checker
        change.comment = reason
        change.save()
        audit_log(
            action="REJECT_BANK_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "bank_request_id": id,
                "checker_id": checker.id
            },
        )
        return JsonResponse({"message": "Bank account creation request rejected successfully"}, status=200)
    except BankChangeRequest.DoesNotExist:
        return JsonResponse({"error": "Bank is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="REJECT_BANK_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"request_id": id,
                        "checker_user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def cancel_bank (request, id):
    try:
        change = BankChangeRequest.objects.get(id=id)
        # reason = request.data.get('reason')
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        edir = change.edir
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()

        change.status = "Cancelled"
        change.approved_at = timezone.now()
        change.checker = checker
        # change.comment = reason
        change.save()
        audit_log(
            action="CANCEL_BANK_REQUEST",
            request=request,
            status="SUCCESS",
            request_data = request.data,
            extra_data={
                "bank_request_id": id,
                "checker_id": checker.id
            },
        )
        return JsonResponse({"message": "Bank account request cancelled successfully"}, status=200)
    except BankChangeRequest.DoesNotExist:
        return JsonResponse({"error": "Bank is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="CANCEL_BANK_REQUEST",
            request=request,
            status="FAILED",
            request_data = request.data,
            extra_data={"request_id": id,
                        "checker_user_id": request.user.id,
                        "error": str(e),
                        "traceback": traceback.format_exc()}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_edir_expenses(request, edir_id):
    try:
        expenses = Fee.objects.filter(
                fee_type="Expense",
                edir_id=edir_id,
                status="Active"
            )
        # expense_serializer = ExpenseDetailSerializer(expenses, many=True)
        paginator = AmbaPagination()
        page = paginator.paginate_queryset(expenses, request)
        serializer = ExpenseDetailSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)
    except Exception as e:
        audit_log(
            action="FETCH_EDIR_EXPENSES",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"edir_id": edir_id,
                        "user_id": request.user.id,
                        "error": str(e),
                        "traceback":traceback.format_exc()}
        )
        return Response(
            {"error": "Failed to fetch expenses list"},
            status=status.HTTP_400_BAD_REQUEST,
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_edir_expense_requests(request, edir_id):
    try:
        expense_request = ExpenseChangeRequest.objects.filter(edir_id=edir_id, status="PENDING")
        serializer = ExpenseChangeRequestSerializer(expense_request, many=True)

        return Response(serializer.data, status=200)
    except Exception as e:
        audit_log(
            action="FETCH_EXPENSE_REQUESTS",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"edir_id": edir_id,
                        "user_id": request.user.id,
                        "error": str(e),
                        "traceback":traceback.format_exc()}
        )
        return Response(
            {"error": "Failed to fetch expenses list"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_expense_detail(request, fee_id):
    try:
        fee = Fee.objects.get(id=fee_id)
        serializer = ExpenseDetailSerializer(fee)

        return Response(serializer.data,status=200)
    except Exception as e:
        audit_log(
            action="FETCH_EXPENSE_DETAIL",
            request=request,
            status="FAILED",
            extra_data={"fee_id": fee_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Fee not found or failed to fetch expense details'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_expense(request, edir_id):
    try:
        data = request.data
        bank = Bank.objects.filter(
            id=data.get("bank"),
        ).first()
        
        if bank and int(bank.amount) < int(data.get("amount", 0)):
            return Response({"amount": "The expense amount exceeds the available balance."}, status=status.HTTP_400_BAD_REQUEST)
        edir = Edir.objects.get(id=edir_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        expense_request = ExpenseChangeRequest.objects.create(
            edir=edir,
            action="CREATE",
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        audit_log(
            action="ADD_EXPENSE_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "edir_id": edir_id,
                "request_id": expense_request.id,
                "maker_user_id": maker.id
            }
        )
        return Response(request.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        audit_log(
            action="ADD_EXPENSE_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_expense(request, fee_id):
    try:
        fee = Fee.objects.get(id=fee_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=fee.edir,
            status="Active"
        ).only("id").first()
        serializer = ExpenseDetailSerializer(fee)
        expense_request = ExpenseChangeRequest.objects.create(
            fee=fee,
            edir=fee.edir,
            action="UPDATE",
            old_value= serializer.data, 
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        audit_log(
            action="UPDATE_EXPENSE_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "fee_id": fee_id,
                "request_id": expense_request.id,
                "maker_user_id": maker.id
            }
        )
        return Response(FeeSerializer(fee).data, status=status.HTTP_201_CREATED)
    except Fee.DoesNotExist:
        return Response({"error": "Expense not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="UPDATE_EXPENSE_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"fee_id": fee_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def disable_expense(request, fee_id):
    try:
        fee = Fee.objects.get(id=fee_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=fee.edir,
            status="Active"
        ).only("id").first()
        serializer = ExpenseDetailSerializer(fee)
        ExpenseChangeRequest.objects.create(
            fee=fee,
            edir=fee.edir,
            action="DISABLE",
            old_value= serializer.data, 
            new_value= request.data,
            maker=maker,
            status="PENDING",
        )
        audit_log(
            action="DISABLE_EXPENSE_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "fee_id": fee_id,
                "maker_user_id": maker.id
            }
        )
        return JsonResponse({"message": "Expense deactivation request recorded successfully",}, status=200)
    except Fee.DoesNotExist:
        return Response({"error": "Bank not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="DISABLE_EXPENSE_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"fee_id": fee_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def approve_expense (request, id):
    try:
        change = ExpenseChangeRequest.objects.get(id=id)
        edir = change.edir
        new = change.new_value
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        category=new.get("category")
        amount=int(new.get("amount")) if new.get("amount") else 0
        supported_member_id=new.get("supported_member") if new.get("supported_member") else None
        bank_id = new.get("bank") if new.get("bank") else None
        payment_method = new.get("method")
        bank = Bank.objects.get(id=bank_id) if bank_id else None

        supported_member = None
        if supported_member_id and (category == "Funeral Contribution" or category == "Sickness Support"):
            supported_member = EdirUser.objects.get(id=supported_member_id)
        else:
            supported_member = None
        
        if change.action == "CREATE":
            if bank and int(bank.amount) < amount:
                return Response({"error": f"Insufficient balance. Available: {bank.amount}, Required: {amount}"}, status=status.HTTP_400_BAD_REQUEST)
            # 1. create expense
            expense = Fee.objects.create(
                edir=edir,
                category=category,
                supported_member = supported_member,
                payment_date = new.get("payment_date"),
                name=new.get("name"),
                reason=new.get("reason"),
                amount=amount,
                status="Active",
                fee_type="Expense", 
            )
            # 2. create deposit
            deposit = Deposit.objects.create(
                transaction_type="WITHDRAW",
                payment_method= payment_method,
                bank_id=bank_id,
                # image=image,
                user=checker,
            )
            # 3. create transaction
            trx = Transaction.objects.create(
                transaction_type="WITHDRAW",
                amount=amount,
                payment_method= payment_method,
                deposit=deposit,
                user= supported_member if supported_member else None,
                edir=edir,
                payment_status="Paid"
            )
            # 4. create transaction change request
            trxRequest = TransactionChangeRequest.objects.create(
                edir=edir,
                user = supported_member if supported_member else None,
                trx =trx,
                action="CREATE",
                new_value=new,
                maker=change.maker,
                status="APPROVED",
                )
            # 5. create fee assignment
            FeeAssignment.objects.create(
                fee=expense, 
                user=supported_member, 
                transaction=trx)
            # 6. update bank balance
            if bank_id:
                bank = Bank.objects.get(id=bank_id)
                bank.amount = bank.amount - amount
                bank.updated_at = timezone.now()
                bank.save()
            audit_log(
                action="APPROVE_CREATE_EXPENSE",
                request=request,
                status="SUCCESS",
                extra_data={
                    "expense_id": expense.id,
                    "request_id": id,
                    "checker_user_id": checker.id
                }
            )
        elif change.action == "UPDATE":
            fee_assign = FeeAssignment.objects.select_related('transaction__deposit__bank').filter(fee=change.fee).first()
            amount_difference = amount - int(fee_assign.transaction.amount if fee_assign and fee_assign.transaction else 0)

            if bank and int(bank.amount) < int(amount_difference):
                return Response(
                    {"error": f"Insufficient balance. Available: {bank.amount}, Required: {amount_difference}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # 1. update expense
            expense=change.fee
            expense.category = category
            expense.name = new.get("name")
            expense.supported_member = supported_member
            expense.amount = amount
            expense.payment_date = new.get("payment_date")
            expense.reason = new.get("reason")
            expense.save()
            # 2. create new deposit
            deposit = Deposit.objects.create(
                transaction_type="WITHDRAW",
                payment_method= payment_method,
                bank_id=bank_id,
                # image=image,
                user=checker,
            )
            # 3. create new transaction
            trx = Transaction.objects.create(
                transaction_type="WITHDRAW",
                amount=amount,
                payment_method=payment_method,
                deposit=deposit,
                user= supported_member if supported_member else None,
                edir=edir,
                payment_status="Paid"
            )
            # 4. create new transaction request
            trx_data = model_to_dict(trx, exclude=["updated_at", "created_at"])
            trxRequest = TransactionChangeRequest.objects.create(
                edir=edir,
                user = supported_member if supported_member else None,
                trx =trx,
                action="UPDATE",
                new_value=json.loads(json.dumps(trx_data, cls=DjangoJSONEncoder)),
                maker=change.maker,
                status="APPROVED",
                )
            # 5. update previous transaction as reversed 
            if fee_assign and fee_assign.transaction:
                prev_trx = fee_assign.transaction
                prev_trx.payment_status = "REVERSED"
                prev_trx.updated_at = timezone.now()
                prev_trx.save()
            # 6. update fee assignment with new transaction
            if fee_assign:
                fee_assign.transaction = trx
                fee_assign.user=supported_member if supported_member else None
                fee_assign.updated_date = timezone.now()
                fee_assign.save()
            # 7. update bank balance with reversed amount
            if fee_assign and fee_assign.transaction and fee_assign.transaction.deposit and fee_assign.transaction.deposit.bank:
                bank.amount = bank.amount + int(fee_assign.transaction.amount)  
                bank.updated_at = timezone.now()
                bank.save()
            # 8. update bank balance with new amount
            if bank_id:
                bank = Bank.objects.get(id=bank_id)
                bank.amount = bank.amount - amount 
                bank.updated_at = timezone.now()
                bank.save()
            audit_log(
                action="APPROVE_UPDATE_EXPENSE",
                request=request,
                status="SUCCESS",
                extra_data={
                    "expense_id": expense.id,
                    "request_id": id,
                    "checker_user_id": checker.id
                }
            )
        elif change.action == "DISABLE":
            fee_assign = FeeAssignment.objects.select_related('transaction__deposit__bank').filter(fee=change.fee).first()
            bank = fee_assign.transaction.deposit.bank if fee_assign.transaction and fee_assign.transaction.deposit  else None
            prev_trx = None
            # 1. update previous transaction as disabled
            if fee_assign and fee_assign.transaction:
                prev_trx = fee_assign.transaction
                prev_trx.payment_status = "DISABLED"
                prev_trx.updated_at = timezone.now()
                prev_trx.save()
            # 2. update bank balance with reversed amount
            if bank:
                bank.amount = bank.amount + int(prev_trx.amount) if prev_trx else bank.amount
                bank.updated_at = timezone.now()
                bank.save()
            # 3. update the status of expense
            expense=change.fee
            expense.status = "Not Active"
            expense.updated_date = timezone.now()
            expense.save()
            change.comment = new.get("reason")
            audit_log(
                action="APPROVE_DEACTIVATE_EXPENSE",
                request=request,
                status="SUCCESS",
                extra_data={
                    "expense_id": expense.id,
                    "request_id": id,
                    "checker_user_id": checker.id
                }
            )
        change.fee = expense
        change.status = "APPROVED"
        change.approved_at = timezone.now()
        change.checker = checker
        change.save()
        return JsonResponse({"message": "Expense request approved successfully",}, status=200)
    except Fee.DoesNotExist:
        return JsonResponse({"error": "Expense is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="DISABLE_EXPENSE_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"request_id": id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def reject_expense (request, id):
    try:
        change = ExpenseChangeRequest.objects.get(id=id)
        reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        change.status = "Rejected"
        change.approved_at = timezone.now()
        change.checker = checker
        change.comment= reason
        change.save()
        audit_log(
            action="REJECT_EXPENSE",
            request=request,
            status="SUCCESS",
            extra_data={
                "reason": reason,
                "request_id": id,
                "checker_user_id": checker.id
            }
        )
        return JsonResponse({"message": "Expense request rejected successfully"}, status=200)
    except ExpenseChangeRequest.DoesNotExist:
        return JsonResponse({"error": "Expense change request is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="REJECT_EXPENSE",
            request=request,
            status="FAILED",
            extra_data={"request_id": id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def cancel_expense (request, id):
    try:
        change = ExpenseChangeRequest.objects.get(id=id)
        # reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        change.status = "Cancelled"
        change.approved_at = timezone.now()
        change.checker = checker
        # change.comment= reason
        change.save()
        audit_log(
            action="CANCEL_EXPENSE",
            request=request,
            status="SUCCESS",
            request_data=request.data,
            extra_data={
                "request_id": id,
                "checker_user_id": checker.id
            }
        )
        return JsonResponse({"message": "Expense request cancelled successfully"}, status=200)
    except ExpenseChangeRequest.DoesNotExist:
        return JsonResponse({"error": "Expense change request is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="CANCEL_EXPENSE",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"request_id": id,
                        "user_id": request.user.id,
                        "error": str(e),
                        "traceback": traceback.format_exc()}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_edir_incomes(request, edir_id):
    try:
        incomes = Fee.objects.filter(
                fee_type="Income",
                edir_id=edir_id,
                status="Active"  
            )
        # income_serializer = FeeDetailSerializer(incomes, many=True)
        paginator = AmbaPagination()
        page = paginator.paginate_queryset(incomes, request)
        serializer = FeeDetailSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)
        # return Response({income_serializer.data}, status=200)
    except Exception as e:
        audit_log(
            action="FETCH_INCOMES",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"edir_id": edir_id,
                        "user_id": request.user.id,
                        "error": str(e),
                        "traceback":traceback.format_exc()}
        )
        return Response(
            {"error": "Failed to fetch daily edir incomes list"},
            status=status.HTTP_400_BAD_REQUEST,
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_income_requests_and_undeposited(request, edir_id):
    try:
        undeposited_trxs = (
            Transaction.objects.filter(
                payment_method="CASH",
                edir_id=edir_id,
                deposit__isnull=True
            )
            .prefetch_related("feeassignment_trx__fee")
            .order_by("-id")
        )
        serializer = UndepositedTransactionSerializer(undeposited_trxs, many=True)
        
        incomeRequest = IncomeChangeRequest.objects.filter(edir_id=edir_id, status="PENDING")
        income_request_serializer = ExpenseChangeRequestSerializer(incomeRequest, many=True)
        return Response({"undeposited": serializer.data, "income_requests": income_request_serializer.data}, status=200)
    except Exception as e:
        audit_log(
            action="GET_DEPOSIT_TRANSACTION",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"edir_id": edir_id,
                        "user_id": request.user.id,
                        "error": str(e),
                        "traceback":traceback.format_exc()}
        )
        return Response(
            {"error": "Failed to fetch daily edir incomes list"},
            status=status.HTTP_400_BAD_REQUEST,
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_income_detail(request, fee_id):
    try:
        fee = Fee.objects.get(id=fee_id)
        serializer = IncomeDetailSerializer(fee)
        return Response( serializer.data,  status=200 )
    except Exception as e:
        audit_log(
            action="GET_DEPOSIT_TRANSACTION",
            request=request,
            status="FAILED",
            extra_data={"fee_id": fee_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Fee not found or failed to fetch income details'},
            status=status.HTTP_404_NOT_FOUND
        )
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_income(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        IncomeChangeRequest.objects.create(
            edir=edir,
            action="CREATE",
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        audit_log(
            action="ADD_INCOME",
            request=request,
            status="SUCCESS",
            extra_data={
                "edir_id": edir_id,
                "maker_user_id": maker.id
            }
        )
        return Response(request.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        audit_log(
            action="ADD_INCOME",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_income(request, fee_id):
    try:
        fee = Fee.objects.get(id=fee_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=fee.edir,
            status="Active"
        ).only("id").first()
        serializer = IncomeDetailSerializer(fee)
        IncomeChangeRequest.objects.create(
            fee=fee,
            edir=fee.edir,
            action="UPDATE",
            old_value= serializer.data, 
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        audit_log(
            action="UPDATE_INCOME_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "fee_id": fee_id,
                "maker_user_id": maker.id
            }
        )
        return Response(FeeSerializer(fee).data, status=status.HTTP_201_CREATED)
    except Fee.DoesNotExist:
        return Response({"error": "Income fee not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="UPDATE_INCOME_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"fee_id": fee_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def disable_income(request, fee_id):
    try:
        fee = Fee.objects.get(id=fee_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=fee.edir,
            status="Active"
        ).only("id").first()
        serializer = ExpenseDetailSerializer(fee)
        IncomeChangeRequest.objects.create(
            fee=fee,
            edir=fee.edir,
            action="DISABLE",
            old_value= serializer.data, 
            new_value= request.data,
            maker=maker,
            status="PENDING",
        )
        audit_log(
            action="DEACTIVATE_INCOME_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "fee_id": fee_id,
                "maker_user_id": maker.id
            }
        )
        return JsonResponse({"message": "Income deactivation request recorded successfully"}, status=200)
    except Fee.DoesNotExist:
        return Response({"error": "Income not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="DEACTiVATE_INCOME_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"fee_id": fee_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def approve_income (request, id):
    try:
        change = IncomeChangeRequest.objects.get(id=id)
        edir = change.edir
        new = change.new_value
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        fee_assign = FeeAssignment.objects.select_related('transaction__deposit__bank').filter(fee=change.fee).first() 
        prev_trx = None
        category=new.get("category")
        amount=int(new.get("amount")) if new.get("amount") else 0
        bank_id = new.get("bank") if new.get("bank") else None
        supported_member_id=new.get("supported_member")
        payment_method = new.get("method")

        supported_member = None
        if supported_member_id and (category == "Donation Contribution"):
            supported_member = EdirUser.objects.get(id=supported_member_id)
        else:
            supported_member = None
        
        if change.action == "CREATE":
            # 1. create Fee
            income = Fee.objects.create(
                edir=edir,
                category=category,
                supported_member = supported_member,
                payment_date = new.get("payment_date"),
                name=new.get("name"),
                reason=new.get("reason"),
                amount=amount,
                status="Active",
                fee_type="Income", 
            )
            # 2. create deposit
            deposit = Deposit.objects.create(
                transaction_type="PAYMENT",
                payment_method= payment_method,
                bank_id=bank_id,
                # image=image,
                user=checker,
            )
            # 3. create transaction
            trx = Transaction.objects.create(
                transaction_type="PAYMENT",
                amount=amount,
                payment_method=payment_method,
                deposit=deposit,
                # image=image,
                user= supported_member if supported_member else None,
                edir=edir,
                payment_status="Paid"
            )
            # 4. create transaction request
            trxRequest = TransactionChangeRequest.objects.create(
                edir=edir,
                user = supported_member if supported_member else None,
                trx =trx,
                action="CREATE",
                new_value=new,
                maker=change.maker,
                status="APPROVED",
                )
            # 5. create fee assignment 
            FeeAssignment.objects.create(
                fee=income, 
                user=supported_member if supported_member else None,
                transaction=trx)
            # 6. deposit to the bank account
            if bank_id:
                bank = Bank.objects.get(id=bank_id)
                bank.amount = bank.amount + amount
                bank.updated_at = timezone.now()
                bank.save()
            audit_log(
                action="APPROVE_CREATE_INCOME",
                request=request,
                status="SUCCESS",
                extra_data={
                    "request_id": id,
                    "checker_user_id": checker.id
                }
            )
        elif change.action == "UPDATE":
            income=change.fee
            # 1. update income fee
            income.category = category
            income.name = new.get("name")
            income.supported_member = supported_member
            income.amount = amount
            income.payment_date = new.get("payment_date")
            income.reason = new.get("reason")
            income.save()
            # 2. create deposit
            deposit = Deposit.objects.create(
                transaction_type="PAYMENT",
                payment_method= payment_method,
                bank_id=bank_id,
                # image=image,
                user=checker,
            )
            # 3. craete transaction
            trx = Transaction.objects.create(
                transaction_type="PAYMENT",
                amount=amount,
                payment_method=payment_method,
                edir=edir,
                user=supported_member if supported_member else None,
                payment_status="PAID",
                deposit = deposit 
            )
            # 4. create transaction
            trx_data = model_to_dict(trx, exclude=["updated_at", "created_at, "])
            trxRequest = TransactionChangeRequest.objects.create(
                edir=edir,
                user = supported_member if supported_member else None,
                trx =trx,
                action="UPDATE",
                new_value= json.loads(json.dumps(trx_data, cls=DjangoJSONEncoder)),
                maker=change.maker,
                status="APPROVED",
                )
            # 5. update previous transaction as reversed
            if fee_assign: 
                prev_trx = fee_assign.transaction
                prev_trx.payment_status="REVERSED"
                prev_trx.updated_at = timezone.now()
                prev_trx.save()
            # 6. update fee assignment 
            if fee_assign:
                fee_assign.transaction = trx
                fee_assign.user=supported_member if supported_member else None
                fee_assign.updated_at = timezone.now()
                fee_assign.save()
            # 7. update bank account balance with previous value
            if fee_assign and fee_assign.transaction and fee_assign.transaction.deposit and fee_assign.transaction.deposit.bank:
                bank.amount = bank.amount - int(fee_assign.transaction.amount)  
                bank.updated_at = timezone.now()
                bank.save()
            # 8. update bank account balance with new value
            if bank_id:
                bank = Bank.objects.get(id=bank_id)
                bank.amount = bank.amount  + amount 
                bank.updated_at = timezone.now()
                bank.save()
            audit_log(
                action="APPROVE_UPDATE_INCOME",
                request=request,
                status="SUCCESS",
                extra_data={
                    "request_id": id,
                    "checker_user_id": checker.id
                }
            )
        elif change.action == "DISABLE": 
            fee_assign = FeeAssignment.objects.select_related('transaction__deposit__bank').filter(fee=change.fee).first()
            bank = fee_assign.transaction.deposit.bank if fee_assign.transaction and fee_assign.transaction.deposit  else None
               
            if bank and int(bank.amount) < fee_assign.transaction.amount if fee_assign and fee_assign.transaction else 0:
                return Response(
                    {"error": f"Insufficient balance. Available: {bank.amount}, Required: {fee_assign.transaction.amount}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            income=change.fee
            # 1. update the income
            income.status = "Not Active"
            income.updated_date = timezone.now()
            income.save()
            # 2. update the transaction status
            if fee_assign:
                prev_trx = fee_assign.transaction
                prev_trx.payment_status="DISABLED"
                prev_trx.updated_at = timezone.now()
                prev_trx.save()
            # 3. update bank account balance
            if bank:
                bank.amount = bank.amount - int(prev_trx.amount)  if prev_trx else bank.amount 
                bank.updated_at = timezone.now()
                bank.save()
            audit_log(
                action="APPROVE_DEACTIVATE_INCOME",
                request=request,
                status="SUCCESS",
                extra_data={
                    "request_id": id,
                    "checker_user_id": checker.id
                }
            )
            change.comment = new.get("reason")
        change.fee = income
        change.status = "APPROVED"
        change.approved_at = timezone.now()
        change.checker = checker
        change.save()
        return JsonResponse({"message": "Income request approved successfully",}, status=200)
    except IncomeChangeRequest.DoesNotExist:
        return JsonResponse({"error": "Income change request is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="APPROVE_INCOME",
            request=request,
            status="FAILED",
            extra_data={"request_id": id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def reject_income (request, id):
    try:
        change = IncomeChangeRequest.objects.get(id=id)
        reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        change.status = "Rejected"
        change.approved_at = timezone.now()
        change.checker = checker
        change.comment= reason
        change.save()
        audit_log(
                action="REJECT_INCOME",
                request=request,
                status="SUCCESS",
                extra_data={
                    "request_id": id,
                    "reason": reason,
                    "checker_user_id": checker.id
                }
            )
        return JsonResponse({"message": "Income request rejected successfully",}, status=200)
    except IncomeChangeRequest.DoesNotExist:
        return JsonResponse({"error": "Income change request is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="REJECT_INCOME",
            request=request,
            status="FAILED",
            extra_data={"fee_id": id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def cancel_income (request, id):
    try:
        change = IncomeChangeRequest.objects.get(id=id)
        # reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        change.status = "Cancelled"
        change.approved_at = timezone.now()
        change.checker = checker
        # change.comment= reason
        change.save()
        audit_log(
                action="CANCEL_INCOME",
                request=request,
                status="SUCCESS",
                request_data=request.data,
                extra_data={
                    "request_id": id,
                    "checker_user_id": checker.id
                }
            )
        return JsonResponse({"message": "Income request cancelled successfully",}, status=200)
    except IncomeChangeRequest.DoesNotExist:
        return JsonResponse({"error": "Income change request is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="CANCEL_INCOME",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"fee_id": id,
                        "user_id": request.user.id,
                        "error": str(e),
                        "traceback":traceback.format_exc()}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_edir_fees(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
        fees =  Fee.objects.filter(
                edir=edir,
                status="Active",
                fee_type="Fee",
            )
        
        # serializer = FeeDetailSerializer(fees, many=True)
        paginator = AmbaPagination()
        page = paginator.paginate_queryset(fees, request)
        serializer = FeeDetailSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)
        # return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Edir.DoesNotExist:
        return Response({"error": "Edir not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="FETCH_FEES",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"edir_id": edir_id,
                        "user_id": request.user.id,
                        "error": str(e),
                        "traceback":traceback.format_exc()}
        )
        return Response(
            {"error": "Failed to fetch edir fees list"},
            status=status.HTTP_400_BAD_REQUEST,
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_edir_fee_requests(request, edir_id):
    try:
        feeRequest = FeeChangeRequest.objects.filter(edir_id=edir_id, status="PENDING")
        serializer = FeeChangeRequestSerializer(feeRequest, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        audit_log(
            action="FETCH_FEE_REQUESTS",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"edir_id": edir_id,
                        "user_id": request.user.id,
                        "error": str(e),
                        "traceback": traceback.format_exc()}
        )
        return Response(
            {"error": "Failed to fetch payment requests"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_fee_detail(request, fee_id):
    try:
        fee = Fee.objects.get(id=fee_id)
        serializer = FeeDetailSerializer(fee)

        return Response( serializer.data, status=200)
    except Fee.DoesNotExist:
        return Response({"error": "Fee not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="FETCH_FEE_DETAILS",
            request=request,
            status="FAILED",
            extra_data={"fee_id": fee_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Fee not found or failed to fetch fee details'},
            status=status.HTTP_404_NOT_FOUND
        )
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_fee_request_detail(request, id):
    try:
        fee_request = FeeChangeRequest.objects.get(id=id)
        serializer = FeeChangeRequestSerializer(fee_request)

        return Response(serializer.data, status=200)
    except Fee.DoesNotExist:
        return Response({"error": "Fee not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="FETCH_FEE_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"request_id": id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Fee request not found or failed to fetch fee request details'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_fee(request, edir_id):
    data = request.data
    try:
        edir = Edir.objects.get(id=edir_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        category = data.get("category")
        fee_name = data.get("name")
        if category == "Monthly Fee":
            exists = Fee.objects.filter(
                edir=edir,
                category="Monthly Fee",
                name=fee_name,
                status="Active",
            ).exists()
            if exists:
                return Response(
                    {"month_year": "This monthly fee already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )        
        fee_request = FeeChangeRequest.objects.create(
            edir=edir,
            action="CREATE",
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        audit_log(
            action="CREATE_FEE_REQUEST",
            request=request,
            status="SUCCESS",
            request_data=request.data,
            extra_data={
                "edir_id": edir_id,
                "request_id": fee_request.id,
                "maker_user_id": maker.id
            }
        )
        return Response(request.data, status=status.HTTP_201_CREATED)
    except Edir.DoesNotExist:
        return Response({"error": "Edir not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="CREATE_FEE_REQUEST",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"edir_id": edir_id,
                        "user_id": request.user.id,
                        "error": str(e),
                        "traceback": traceback.format_exc(),}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_fee(request, fee_id):
    try:
        fee = Fee.objects.get(id=fee_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=fee.edir,
            status="Active"
        ).only("id").first()
        old_value = model_to_dict(fee, exclude=["updated_date"])
        if old_value.get("payment_date"):
            old_value["payment_date"] = old_value["payment_date"].isoformat()

        if old_value.get("created_date"):
            old_value["created_date"] = old_value["created_date"].isoformat()

        assigned_users = FeeAssignment.objects.filter(fee=fee).values_list("user_id", flat=True)

        old_value["users"] = list(assigned_users)
        fee_request = FeeChangeRequest.objects.create(
            fee=fee,
            edir=fee.edir,
            action="UPDATE",
            old_value= old_value,
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        audit_log(
            action="UPDATE_FEE_REQUEST",
            request=request,
            status="SUCCESS",
            request_data=request.data,
            extra_data={
                "edir_id": fee.edir.id,
                "fee_id": fee_id,
                "request_id": fee_request.id,
                "maker_user_id": maker.id
            }
        )
        return Response(FeeSerializer(fee).data, status=status.HTTP_201_CREATED)
    except Fee.DoesNotExist:
        return Response({"error": "Fee not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="UPDATE_FEE_REQUEST",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"fee_id": fee_id,
                        "user_id": request.user.id,
                        "error": str(e),
                        "traceback": traceback.format_exc(),}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def disable_fee(request, fee_id):
    try:
        fee = Fee.objects.get(id=fee_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=fee.edir,
            status="Active"
        ).only("id").first()
        old_value = model_to_dict(fee, exclude=["updated_date"])
        if old_value.get("payment_date"):
            old_value["payment_date"] = old_value["payment_date"].isoformat()

        if old_value.get("created_date"):
            old_value["created_date"] = old_value["created_date"].isoformat()

        assigned_users = FeeAssignment.objects.filter(fee=fee).values_list("user_id", flat=True)
        old_value["users"] = list(assigned_users)

        request = FeeChangeRequest.objects.create(
            fee=fee,
            edir=fee.edir,
            action="DISABLE",
            old_value= old_value, 
            new_value= request.data,
            maker=maker,
            status="PENDING",
        )
        audit_log(
            action="DISABLE_FEE_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "edir_id": fee.edir.id,
                "fee_id": fee_id,
                "request_id": request.id,
                "maker_user_id": maker.id
            }
        )
        return JsonResponse({"message": "Fee deactivation request recorded successfully"}, status=200)
    except Fee.DoesNotExist:
        return Response({"error": "Bank not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="DISABLE_FEE_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"fee_id": fee_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def approve_fee (request, id):
    try:
        change = FeeChangeRequest.objects.get(id=id)
        edir = change.edir
        new = change.new_value
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        category = new.get("category")
        fee_name = new.get("name")
        supported_member_id = new.get("supported_member")

        supported_member = None
        if supported_member_id and (category == "Funeral Contribution" or category == "Sickness Support"):
            supported_member = EdirUser.objects.get(id=supported_member_id)
        else:
            supported_member = None
        
        if change.action == "CREATE":
            if category == "Monthly Fee":
                exists = Fee.objects.filter(
                    edir=edir,
                    category="Monthly Fee",
                    name=fee_name,
                    status="Active",
                ).exists()
                if exists:
                    return Response(
                        {
                            "month_year": "This monthly fee already exists.",
                            "error": "This monthly fee already exists."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            fee = Fee.objects.create(
                edir=edir,
                category=category,
                name=fee_name,
                supported_member = supported_member,
                reason=new.get("reason"),
                amount=new.get("amount"),
                payment_date=new.get("payment_date"),
            )
            change.fee =fee
            user_ids = new.get("users", [])
            for uid in user_ids:
                user = EdirUser.objects.get(id=uid)
                if supported_member and user == supported_member:
                    continue
                else:
                    FeeAssignment.objects.create(fee=fee, user=user)#, maker = request.user
            audit_log(
                action="APPROVE_CREATE_FEE",
                request=request,
                status="SUCCESS",
                extra_data={
                    "edir_id": fee.edir.id,
                    "fee_id": fee.id,
                    "request_id": id,
                    "checker_user_id": checker.id
                }
            )
        elif change.action == "UPDATE":
            fee=change.fee
            if category == "Monthly Fee":
                exists = Fee.objects.filter(
                    edir=edir,
                    category="Monthly Fee",
                    name=fee_name,
                    status="Active",
                ).exclude(id=fee.id).exists()
                if exists:
                    return Response(
                        {
                            "month_year": "This monthly fee already exists.",
                            "error": "This monthly fee already exists."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            fee.category = new.get("category", fee.category)
            fee.name = new.get("name", fee.name)
            fee.reason = new.get("reason", fee.reason)
            fee.amount = new.get("amount", fee.amount)
            fee.payment_date = new.get("payment_date", fee.payment_date)
            fee.supported_member = supported_member
            fee.save()

            user_ids = new.get("users", [])
            existing_assignments = FeeAssignment.objects.filter(fee=fee)
            for fee_assign in existing_assignments:
                if str(fee_assign.user.id) not in user_ids:
                    fee_assign.status = "Disabled" #?????
                    fee_assign.updated_date = timezone.now()
                    fee_assign.save()

            for uid in user_ids:
                try:
                    user = EdirUser.objects.get(id=uid)
                    existing_assignment = FeeAssignment.objects.filter(fee=fee, user=user, status="Active").exists()
                    if not existing_assignment:
                        if str(uid) == str(supported_member_id):
                            continue
                        else:
                            FeeAssignment.objects.create(fee=fee, user=user)
                except EdirUser.DoesNotExist:
                    continue
            audit_log(
                action="APPROVE_UPDATE_FEE",
                request=request,
                status="SUCCESS",
                extra_data={
                    "edir_id": fee.edir.id,
                    "fee_id": fee.id,
                    "request_id": id,
                    "checker_user_id": checker.id
                }
            )
        elif change.action == "DISABLE":
            fee=change.fee
            fee.status = "Not Active"
            fee.updated_date = timezone.now()
            fee.save()

            existing_assignments = FeeAssignment.objects.filter(fee=fee)
            for fee_assign in existing_assignments:
                fee_assign.status = "Disabled" 
                fee_assign.save()
            audit_log(
                action="APPROVE_DEISABLE_FEE",
                request=request,
                status="SUCCESS",
                extra_data={
                    "edir_id": fee.edir.id,
                    "fee_id": fee.id,
                    "request_id": id,
                    "checker_user_id": checker.id
                }
            )
            change.comment = new.get("reason")
        change.fee = fee
        change.status = "APPROVED"
        change.approved_at = timezone.now()
        change.checker = checker
        change.save()
        return JsonResponse({"message": "Fee request approved successfully",}, status=200)
    except FeeChangeRequest.DoesNotExist:
        return JsonResponse({"error": "Fee is not found "}, status=404)
    except EdirUser.DoesNotExist:
        return Response({"error": "Checker not found."}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        audit_log(
            action="APPROVE_FEE",
            request=request,
            status="FAILED",
            extra_data={"request_id": id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Fee approval failed due to Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )   

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def reject_fee (request, id):
    try:
        change = FeeChangeRequest.objects.get(id=id)
        reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        change.status = "Rejected"
        change.approved_at = timezone.now()
        change.checker = checker
        change.comment= reason
        change.save()
        audit_log(
            action="REJECT_FEE",
            request=request,
            status="SUCCESS",
            extra_data={
                "request_id": id,
                "reason": reason,
                "checker_user_id": checker.id
            }
        )
        return JsonResponse({"message": "Fee request rejected successfully"}, status=200)
    except FeeChangeRequest.DoesNotExist:
        return JsonResponse({"error": "Fee request is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="REJECT_FEE",
            request=request,
            status="FAILED",
            extra_data={"request_id": id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def cancel_fee (request, id):
    try:
        change = FeeChangeRequest.objects.get(id=id)
        # reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        change.status = "Cancelled"
        change.approved_at = timezone.now()
        change.checker = checker
        # change.comment= reason
        change.save()
        audit_log(
            action="CANCEL_FEE",
            request=request,
            status="SUCCESS",
            request_data=request.data,
            extra_data={
                "request_id": id,
                "checker_user_id": checker.id
            }
        )
        return JsonResponse({"message": "Fee request cancelled successfully"}, status=200)
    except FeeChangeRequest.DoesNotExist:
        return JsonResponse({"error": "Fee request is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="CANCEL_FEE",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"request_id": id,
                        "user_id": request.user.id,
                        "error": str(e),
                        "traceback":traceback.format_exc()}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_unpaid_fees(request, user_id):
    try:
        user = EdirUser.objects.get(id=user_id)
        pending_requests = FeeAssignmentTrxChangeRequest.objects.filter(
            fee_assignment=OuterRef("pk"),
            trx_change_request__status="PENDING"
        )
        unpaid_fees = (
            FeeAssignment.objects.filter(
                status="Active",
                user=user,
                transaction=None
            )
            .annotate(has_pending=Exists(pending_requests))
            .filter(has_pending=False)
            .order_by("-id")
            .select_related("fee")
        )
        serializer = FeeAssignmentSerializer(unpaid_fees, many = True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except EdirUser.DoesNotExist:
        return JsonResponse({"error": "User is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="FETCH_UNPAID_FEE",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"user_id": user_id,
                        "fetcher_id": request.user.id,
                        "error": str(e),
                        "traceback":traceback.format_exc()}
        )
        return Response(
            {"error": "Failed to unpaid fees list"},
            status=status.HTTP_400_BAD_REQUEST,
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_unpaid_fees_paginated(request, user_id):
    try:
        user = EdirUser.objects.get(id=user_id)
        pending_requests = FeeAssignmentTrxChangeRequest.objects.filter(
            fee_assignment=OuterRef("pk"),
            trx_change_request__status="PENDING"
        )
        unpaid_fees = (
            FeeAssignment.objects.filter(
                status="Active",
                user=user,
                transaction=None
            )
            .annotate(has_pending=Exists(pending_requests))
            .filter(has_pending=False)
            .order_by("-id")
            .select_related("fee")
        )
        paginator = AmbaPagination()
        page = paginator.paginate_queryset(unpaid_fees, request)
        serializer = FeeAssignmentSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)
        # serializer = FeeAssignmentSerializer(unpaid_fees, many = True)
        # return Response(serializer.data, status=status.HTTP_200_OK)
    except EdirUser.DoesNotExist:
        return JsonResponse({"error": "User is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="FETCH_UNPAID_FEE_PAGINATED",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"user_id": user_id,
                        "fetcher_id": request.user.id,
                        "error": str(e),
                        "traceback":traceback.format_exc()}
        )
        return Response(
            {"error": "Failed to unpaid fees list"},
            status=status.HTTP_400_BAD_REQUEST,
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_paid_fees(request, ref):
    try:
        trx = Transaction.objects.select_related("deposit__bank").get(reference=ref)
        paid_fees = FeeAssignment.objects.select_related("fee").filter(transaction=trx)
        
        serializer = FeeAssignmentSerializer(paid_fees, many = True)
        return Response({
            "fees": serializer.data,
            "payment_method": trx.payment_method if trx else None,
            "bank": trx.deposit.bank.id if trx and trx.deposit and trx.deposit.bank else None,
            "image": request.build_absolute_uri(trx.deposit.image.url) if trx.deposit and trx.deposit.image else None
            }, status=status.HTTP_200_OK)
    except Transaction.DoesNotExist:
        return JsonResponse({"error": "Transaction is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="FETCH_PAID_FEE",
            request=request,
            status="FAILED",
            extra_data={"trx_ref": ref,
                        "fetcher_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {"error": "Failed to get paid fees list"},
            status=status.HTTP_400_BAD_REQUEST,
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_payments(request, user_id):
    try:
        current_user = EdirUser.objects.get(id=user_id)
        payments = (
            Transaction.objects.filter(
                user=current_user,
                payment_status__in=["Paid","PAID"],
            )
            .annotate(
                fee_count=Count("feeassignment_trx", distinct=True)
            )
            .order_by("-created_at")
        )
        paginator = AmbaPagination()
        page = paginator.paginate_queryset(payments, request)
        serializer = PaymentHistorySerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)

    except Exception as e:
        audit_log(
            action="FETCH_USER_PAYMENT",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={"edir_user_id": user_id,
                        "user_id": request.user.id,
                        "error": str(e),
                        "traceback": traceback.format_exc()}
        )
        return Response(
            {"error": "Failed to fetch payments"},
            status=status.HTTP_400_BAD_REQUEST,
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_payment_requests(request, user_id):
    try:
        current_user = EdirUser.objects.get(id=user_id)
        payment_request = TransactionChangeRequest.objects.filter(edir=current_user.edir, 
                                                                  user= current_user, 
                                                                  status="PENDING")
        serializer = PaymentChangeRequestSerializer(payment_request, 
                                                    many=True, 
                                                    context={'request': request})

        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        audit_log(
            action="FETCH_PAYMENT_REQUESTS",
            request=request,
            status="FAILED",
            extra_data={"edir_user_id": user_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {"error": "Failed to fetch payment requests"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_payment_detail(request, ref):
    try:
        trx = (
            Transaction.objects
            .filter(reference=ref)
            .select_related("deposit")
            .prefetch_related("feeassignment_trx__fee")  
            .first()
        )
        serializer = TransactionSerializer(trx, context={"request": request})

        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        audit_log(
            action="FETCH_PAYMENT_DETAILSS",
            request=request,
            status="FAILED",
            extra_data={"trx_ref": ref,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {"error": "Failed to fetch payments"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_deposit_detail(request, id):
    try:
        deposit = Deposit.objects.annotate(total_amount=Sum("transactions__amount")).get(id=id)
        trx = (
            Transaction.objects
            .filter(deposit_id=id)
            .prefetch_related("feeassignment_trx__fee")   
        )

        serializer = TransactionSerializer(trx, context={"request": request}, many=True)
        deposit_serializer = SimpleDepositSerializer(deposit)

        return Response({"trxs" : serializer.data, "deposit": deposit_serializer.data}, status=status.HTTP_200_OK)
    except Deposit.DoesNotExist:
        return Response({'error': 'Deposit not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="FETCH_DEPOSIT_DETAILS",
            request=request,
            status="FAILED",
            extra_data={"deposit_id": id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {"error": "Failed to fetch payments"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_undeposited_trxs(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
        undeposited_trxs = (
            Transaction.objects.filter(
                payment_method="CASH",
                edir=edir,
                deposit__isnull=True
            )
            .order_by("-id")
        )
        data = [
            {
                "id": a.id,
                "amount": a.amount,
                "user": {
                    "id": a.user.id,
                    "full_name": a.user.full_name,
                } if a.user else None,
                "payment_date": a.created_at.isoformat(),
            }
            for a in undeposited_trxs
        ]
        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        audit_log(
            action="FETCH_UNDEPOSIT_TRXS",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {"error": "Failed to fetch undeposited transactions list"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def make_transfer(request, edir_id):
    fees_data = request.data.get("fees", "[]")
    fees_data = json.loads(fees_data)
    user_id = request.data.get("userId")
    ref= request.data.get("ref")
    data = {
        "fees": fees_data,
        "bank": request.data.get("bank"),
        "total_amount": request.data.get("total_amount"),
        "method": request.data.get("method"),
    }
    image = request.FILES.get("image")
    if image:
        data["image_name"] = image.name
    data.pop("image", None)
    
    trx = None
    try:
        edir = Edir.objects.get(id=edir_id)
        user = EdirUser.objects.get(id=user_id)
        trx = Transaction.objects.filter(reference=ref).first()
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()

        trx_request = TransactionChangeRequest.objects.create(
            edir=edir,
            user=user,
            trx=trx,
            action="CREATE",
            new_value=data,
            maker=maker,
            status="PENDING",
            image=image,
        )
        for fee in fees_data:
            fee_assignment = FeeAssignment.objects.filter(
                fee_id=fee,
                user=user,
                status="Active",
            ).first()

            if fee_assignment:
                FeeAssignmentTrxChangeRequest.objects.create(
                    fee_assignment=fee_assignment,
                    trx_change_request=trx_request,
                )
                fee_assignment.transaction_change_request = trx_request
                fee_assignment.save()
        audit_log(
            action="MAKE_TRANSFER",
            request=request,
            status="SUCCESS",
            extra_data={
                "edir_id": edir_id,
                "user_id": user_id,
                "maker_user_id": maker.id
            }
        )
        return Response({'message': 'transfer trx added by user'}, status=status.HTTP_201_CREATED)
    except Edir.DoesNotExist:
        return Response({'error': 'edir not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="MAKE_TRANSFER",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {"error": "Internal server error"},
            status=500,
        )

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def admin_receive_cashes(request, edir_id):
    try:
        user_id = request.data.get("userId")
        total_amount = request.data.get("total_amount")
        method = request.data.get("method")
        fees_data = request.data.get("fees", [])
        fees_data = json.loads(fees_data) if isinstance(fees_data, str) else fees_data
        data = {
            "fees": fees_data,
            "bank": request.data.get("bank"),
            "total_amount": request.data.get("total_amount"),
            "method": request.data.get("method"),
        }
        edir = Edir.objects.get(id=edir_id)
        member = EdirUser.objects.get(id=user_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        # 1. create transaction
        trx = Transaction.objects.create(
            transaction_type="PAYMENT",
            amount=total_amount,
            payment_method=method,
            edir=edir,
            user=member,
            payment_status="PAID"
        )
        # 2. transaction request created
        trx_request = TransactionChangeRequest.objects.create(
            edir=edir,
            user=member,
            trx=trx,
            action="CREATE",
            new_value=data,
            maker=maker,
            status="PAID",
        )
        # 3. update fee assignment transaction request and create fee_assignment_transaction_request
        for fee in fees_data:
            fee_assignment = FeeAssignment.objects.filter(
                fee_id=fee,
                user=member,
                status="Active",
            ).first()

            if fee_assignment:
                FeeAssignmentTrxChangeRequest.objects.create(
                    fee_assignment=fee_assignment,
                    trx_change_request=trx_request,
                )
                fee_assignment.transaction_change_request = trx_request
                fee_assignment.save()
        fee_ids = [f["id"] for f in fees_data] if isinstance(fees_data, str) else fees_data
        # 4. update fee assignment transaction
        for fee_id in fee_ids:
            fee_assign = FeeAssignment.objects.get(fee_id=fee_id, user = member, transaction__isnull=True)
            fee_assign.updated_date = timezone.now()
            fee_assign.transaction = trx
            fee_assign.save()   
        audit_log(
            action="ADMIN_RECEIVE_CASHES",
            request=request,
            status="SUCCESS",
            extra_data={
                "edir_id": edir_id,
                "user_id": user_id,
                "maker_user_id": maker.id
            }
        )
        return Response({'message': 'cash payment added by committee member'}, status=status.HTTP_201_CREATED)
    
    except Edir.DoesNotExist:
        return Response({'error': 'edir not found'}, status=status.HTTP_404_NOT_FOUND)
    except EdirUser.DoesNotExist:
        return Response({'error': 'edir user not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="ADMIN_RECEIVE_CASHES",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {"error": "Internal server error"},
            status=500,
        )

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def deposit_payments(request, edir_id):
    # user_id = request.data.get("userId")
    total_amount = int(request.data.get("total_amount"))
    bank_id = request.data.get("bank")
    cashes_data = request.data.get("cashes", [])
    cashes_data = json.loads(cashes_data) if isinstance(cashes_data, str) else cashes_data
    data = {
        "cashes": cashes_data,
        "bank": request.data.get("bank"),
        "total_amount": request.data.get("total_amount"),
    }
    
    image = request.FILES.get("image")
    if image:
        data["image_name"] = image.name
    data.pop("image", None)
    try:
        edir = Edir.objects.get(id=edir_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        
        deposit = Deposit.objects.create(
            transaction_type="PAYMENT",
            payment_method="CASH",
            bank_id=bank_id,
            image=image,
            user=maker,
        )
        # deposit_request = DepositChangeRequest.objects.create(
        #     edir=edir,
        #     deposit=deposit,
        #     action="CREATE",
        #     new_value=data,
        #     maker=maker,
        #     status="PAID",
        # )
        for cash_id in cashes_data:
            trx = Transaction.objects.get(id=cash_id)
            trx.updated_date = timezone.now()
            trx.deposit = deposit
            trx.save()
        Bank.objects.filter(id=bank_id).update(
            amount=F("amount") + total_amount,
            updated_date=timezone.now()
        )
        audit_log(
            action="DEPOSIT_CASH_PAYMENTS",
            request=request,
            status="SUCCESS",
            extra_data={
                "edir_id": edir_id,
                "user_id": maker.id,
                "deposit_id": deposit.id,
                "maker_user_id": maker.id
            }
        )
        return Response({'message': 'cash deposited by committee member'}, status=status.HTTP_201_CREATED)
    
    except Edir.DoesNotExist:
        return Response({'error': 'edir not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="DEPOSIT_CASH_PAYMENTS",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {"error": "Internal server error"},
            status=500,
        )

    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_pay_fees(request, edir_id):
    fees_data = request.data.get("fees", "[]")
    fees_data = json.loads(fees_data)
    previous_values = request.data.get("previous_value")
    if previous_values:
        previous_values = json.loads(previous_values)
    user_id = request.data.get("userId")
    ref= request.data.get("ref")
    data = {
        "fees": fees_data,
        "bank": request.data.get("bank"),
        "total_amount": request.data.get("total_amount"),
        "method": request.data.get("method"),
    }
    image = request.FILES.get("image")
    if image:
        data["image_name"] = image.name
    data.pop("image", None)
    
    trx = None
    try:
        edir = Edir.objects.get(id=edir_id)
        user = EdirUser.objects.get(id=user_id)
        trx = Transaction.objects.filter(reference=ref).first()
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()

        trx_request = TransactionChangeRequest.objects.create(
            edir=edir,
            user=user,
            prev_trx=trx,
            action="UPDATE",
            old_value=previous_values,
            new_value=data,
            maker=maker,
            status="PENDING",
            image=image,
        )
        for fee in fees_data:
            fee_assignment = FeeAssignment.objects.filter(
                fee_id=fee,
                user=user,
                status="Active",
            ).first()

            if fee_assignment:
                FeeAssignmentTrxChangeRequest.objects.create(
                    fee_assignment=fee_assignment,
                    trx_change_request=trx_request,
                )
                fee_assignment.transaction_change_request = trx_request
                fee_assignment.save()
        audit_log(
            action="UPDATE_PAY_FEE_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "edir_id": edir_id,
                "user_id": user_id,
                "maker_user_id": maker.id
            }
        )
        return Response({'message': 'transfer trx updated by user'}, status=status.HTTP_201_CREATED)
    except Edir.DoesNotExist:
        return Response({'error': 'edir not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="UPDATE_PAY_FEE_REQUEST",
            request=request,
            status="FAILED",
            extra_data={"edir_id": edir_id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {"error": "Internal server error"},
            status=500,
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def disable_payment(request, ref):
    try:
        trx = (
            Transaction.objects
            .filter(reference=ref)
            .select_related("deposit__bank")
            .prefetch_related("feeassignment_trx__fee")   
            .first()
        )
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=trx.edir,
            status="Active"
        ).only("id").first()
        data = {
            "fees": [
                str(a.fee.id)
                for a in trx.feeassignment_trx.all()   
            ],
            "bank": trx.deposit.bank.id if trx.deposit and trx.deposit.bank else None,
            "total_amount": trx.amount,
            "method": trx.payment_method,
        }

        trx_request = TransactionChangeRequest.objects.create(
            trx=trx,
            prev_trx=trx,
            user=trx.user,
            edir=trx.edir,
            action="DISABLE",
            old_value= data, 
            new_value= request.data,
            maker=maker,
            status="PENDING",
            image=trx.deposit.image if trx.deposit else None,
        )
        for fee in data["fees"]:
            fee_assignment = FeeAssignment.objects.filter(
                fee_id=fee,
                user=trx.user,
                status="Active",
            ).first()

            if fee_assignment:
                FeeAssignmentTrxChangeRequest.objects.create(
                    fee_assignment=fee_assignment,
                    trx_change_request=trx_request,
                )
                fee_assignment.transaction_change_request = trx_request
                fee_assignment.save()
        audit_log(
            action="DISABLE_PAYMENT_REQUEST",
            request=request,
            status="SUCCESS",
            extra_data={
                "trx_ref": ref,
                "maker_user_id": maker.id
            }
        )
        return JsonResponse({"message": "Payment deactivation request recorded successfully"}, status=200)

    except Transaction.DoesNotExist:
        return Response({"error": "Transaction not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="UPDATE_PAY_FEE_REQUEST",
            request=request,
            status="FAILED",
            extra_data={
                        "trx_ref": ref,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def approve_payments(request, id):
    trx = None
    try:
        change = TransactionChangeRequest.objects.get(id=id)
        prev_trx = change.prev_trx
        new = change.new_value
        old_value = change.old_value
        edir = change.edir
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        if change.action == "DISABLE": 
            bank_id = old_value.get("bank")
            total_amount = int(old_value.get("total_amount"))
            method = old_value.get("method")
            image = change.image
            old_fees_data = old_value.get("fees", "[]")
            if isinstance(old_fees_data, str):
                old_fee_ids = json.loads(old_fees_data)
            else:
                old_fee_ids = old_fees_data

            # 1. remove transaction data from fee assignments
            for fee_id in old_fee_ids:
                fee_assign = FeeAssignment.objects.get(fee_id=fee_id, user = change.user)
                fee_assign.updated_date = timezone.now()
                fee_assign.transaction = None
                fee_assign.save() 
            # 2. mark transaction as disabled
            if prev_trx:
                prev_trx.payment_status = "Disabled"
                prev_trx.updated_at = timezone.now()
                prev_trx.save()
            # 3. mark deposit as reversed if payment method was transfer
            if prev_trx and prev_trx.deposit and method == "TRANSFER":
                deposit = prev_trx.deposit 
                deposit.payment_status = "Disabled"
                deposit.updated_at = timezone.now()
                deposit.save()
            # 4. update bank amount
            if bank_id:
                bank = Bank.objects.get(id=bank_id)
                bank.amount = bank.amount - prev_trx.amount if prev_trx else bank.amount
                bank.updated_at = timezone.now()
                bank.save()
            audit_log(
                action="APPROVE_DISABLE_PAYMENT",
                request=request,
                status="SUCCESS",
                extra_data={
                    "request_id": id,
                    "checker_user_id": checker.id
                }
            )
        else:
            deposit = None
            fees_data = new.get("fees", "[]")
            bank_id = new.get("bank")
            total_amount = int(new.get("total_amount"))
            method = new.get("method")
            image = change.image
            # user_id = new.get("userId")

            if isinstance(fees_data, str):
                fee_ids = json.loads(fees_data)
            else:
                fee_ids = fees_data
            bank = None
            if bank_id and str(bank_id).isdigit():
                bank = Bank.objects.filter(id=int(bank_id)).first()
            # 1. create deposit if method is transfer
            if bank and method == "TRANSFER":
                deposit = Deposit.objects.create(
                    transaction_type="PAYMENT",
                    payment_method=method,
                    bank=bank,
                    image=image,
                    user=checker,
                )
            # reuse deposit if method is cash and previous trx has deposit
            if prev_trx and method == "CASH":
                deposit = prev_trx.deposit if prev_trx else None
            # 2. create transaction
            trx = Transaction.objects.create(
                transaction_type="PAYMENT",
                amount=total_amount,
                payment_method=method,
                edir=edir,
                user=change.user,
                payment_status="PAID",
                deposit = deposit if deposit else None
            )

            if change.action == "UPDATE":    
                old_fees_data = change.old_value.get("fees", "[]")
                if isinstance(old_fees_data, str):
                    old_fee_ids = json.loads(old_fees_data)
                else:
                    old_fee_ids = old_fees_data
                # 3. remove transaction data from old fee assignments
                for fee_id in old_fee_ids:
                    fee_assign = FeeAssignment.objects.get(fee_id=fee_id, user = change.user)
                    fee_assign.updated_date = timezone.now()
                    fee_assign.transaction = None
                    fee_assign.save() 
                # 4. add transaction data to new fee assignments
                for fee_id in fee_ids:
                    fee_assign = FeeAssignment.objects.get(fee_id=fee_id, user = change.user)
                    fee_assign.updated_date = timezone.now()
                    fee_assign.transaction = trx
                    fee_assign.save() 
                # 5. mark previous transaction as reversed
                if prev_trx:
                    prev_trx.payment_status = "REVERSED"
                    prev_trx.updated_at = timezone.now()
                    prev_trx.save()
                # 6. mark previous deposit as reversed if payment method was transfer
                if prev_trx and prev_trx.deposit and method == "TRANSFER":
                    deposit = prev_trx.deposit 
                    deposit.payment_status = "REVERSED"
                    deposit.updated_at = timezone.now()
                    deposit.save()
                # 7. update bank amount
                if bank:
                    bank.amount = bank.amount - prev_trx.amount + total_amount if prev_trx else bank.amount + total_amount
                    bank.updated_at = timezone.now()
                    bank.save()
                audit_log(
                    action="APPROVE_UPDATE_PAYMENT",
                    request=request,
                    status="SUCCESS",
                    extra_data={
                        "request_id": id,
                        "checker_user_id": checker.id
                    }
                )
            elif change.action == "CREATE":
                if isinstance(fees_data, str):
                    fee_ids = json.loads(fees_data)
                else:
                    fee_ids = fees_data
                # 3. add transaction data to new fee assignments
                for fee_id in fee_ids:
                    fee_assign = FeeAssignment.objects.filter(fee_id=fee_id, user = change.user, transaction__isnull=True).first()
                    if fee_assign:
                        fee_assign.updated_date = timezone.now()
                        fee_assign.transaction = trx
                        fee_assign.save()
                # 4. update bank amount
                Bank.objects.filter(id=bank_id).update(
                    amount=F("amount") + total_amount,
                    updated_date=timezone.now()
                    )
                audit_log(
                    action="APPROVE_CREATE_PAYMENT",
                    request=request,
                    status="SUCCESS",
                    extra_data={
                        "request_id": id,
                        "checker_user_id": checker.id
                    }
                )
                change.trx= trx
        change.status = "Approved"
        change.approved_at = timezone.now()
        change.checker = checker
        change.save()
        return Response({"transaction_id": "payment approved successfully"}, status=201)
    
    except Edir.DoesNotExist:
        return Response({'error': 'edir not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="APPROVE_PAYMENT",
            request=request,
            status="FAILED",
            extra_data={
                        "request_id": id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {"error": "Internal server error"},
            status=500,
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def reject_payment (request, id):
    try:
        change = TransactionChangeRequest.objects.get(id=id)
        reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        change.status = "Rejected"
        change.approved_at = timezone.now()
        change.checker = checker
        change.comment= reason
        change.save()
        audit_log(
            action="REJECT_PAYMENT",
            request=request,
            status="SUCCESS",
            extra_data={
                "request_id": id,
                "reason":reason,
                "checker_user_id": checker.id
            }
        )
        return JsonResponse({"message": "Payment request rejected successfully"}, status=200)
    except TransactionChangeRequest.DoesNotExist:
        return JsonResponse({"error": "Payment request is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="REJECT_PAYMENT",
            request=request,
            status="FAILED",
            extra_data={
                        "request_id": id,
                        "user_id": request.user.id,
                        "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def cancel_payment (request, id):
    try:
        change = TransactionChangeRequest.objects.get(id=id)
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        change.status = "Cancelled"
        change.approved_at = timezone.now()
        change.checker = checker
        change.save()
        audit_log(
            action="CANCEL_PAYMENT",
            request=request,
            status="SUCCESS",
            request_data=request.data,
            extra_data={
                "request_id": id,
                "checker_user_id": checker.id
            }
        )
        return JsonResponse({"message": "Payment request cancelled successfully"}, status=200)
    except TransactionChangeRequest.DoesNotExist:
        return JsonResponse({"error": "Payment request is not found "}, status=404)
    except Exception as e:
        audit_log(
            action="CANCEL_PAYMENT",
            request=request,
            status="FAILED",
            request_data=request.data,
            extra_data={
                        "request_id": id,
                        "user_id": request.user.id,
                        "error": str(e),
                        "traceback": traceback.format_exc(),}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

#change password
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    try:
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        audit_log(
            action="CHANGE_PASSWORD",
            request=request,
            status="SUCCESS",
            extra_data={
                "phone_number":user.phone_number,
                "user_id": user.id
            },
        )
        return Response({'detail': 'Password changed successfully'}, status=status.HTTP_200_OK)
    except Exception as e:
        audit_log(
            action="CHANGE_PASSWORD",
            request=request,
            status="FAILED",
            extra_data={
                "user_id": request.user.id,
                "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def add_event(request, edir_id):
    data = request.data  
    try:
        edir = Edir.objects.get(id=edir_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()

        title = data.get('title')
        description = data.get('description')
        caption = data.get('caption')
        date = data.get('date')
        location = data.get('location')
        image = request.FILES.get("image")

        event = Event.objects.create(
            edir = edir,
            title=title,
            description=description,
            caption=caption,
            date=date,
            location=location,
            image =image,
            made_by = maker,
        )
        event.save()
        audit_log(
            action="ADD_EVENT",
            request=request,
            status="SUCCESS",
            extra_data={
                "edir_id":edir_id,
                "user_id": maker.id
            },
        )
        return Response({'message': 'Event added by admin'}, status=status.HTTP_201_CREATED)

    except Edir.DoesNotExist:
        return Response({'error': 'edir not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="ADD_EVENT",
            request=request,
            status="FAILED",
            extra_data={
                "edir_id":edir_id,
                "user_id": request.user.id,
                "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def edir_event_list(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
        event = Event.objects.filter(edir=edir, status="Active")
        limit = request.query_params.get("limit")
        if limit is not None:
            limit = int(limit)
            event = event[:limit]
        serializer = EventSerializer(event, many=True)
        return Response(serializer.data)
    except Edir.DoesNotExist:
        return Response({"detail": "Edir not added"}, status=status.HTTP_404_NOT_FOUND)
    except Event.DoesNotExist:
        return Response({"detail": "Event not added"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="FETCH_EVENT_LIST",
            request=request,
            status="FAILED",
            extra_data={
                "edir_id":edir_id,
                "user_id": request.user.id,
                "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def popular_event_list(request):
    try:
        event = Event.objects.filter(edir__isnull=True, status="Active")
        serializer = EventSerializer(event, many=True)
        return Response(serializer.data)
    except Event.DoesNotExist:
        return Response({"detail": "Event not added"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="FETCH_POPULAR_EVENT_LIST",
            request=request,
            status="FAILED",
            extra_data={
                "user_id": request.user.id,
                "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def event_detail(request, event_id):
    try:
        event = Event.objects.get(id=event_id)
        if request.method == 'GET':
            serializer = EventSerializer(event)
            return Response(serializer.data)
        elif request.method == "PUT":
            serializer = EventSerializer(event, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Event.DoesNotExist:
        return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        audit_log(
            action="EVENT_DETAIL",
            request=request,
            status="FAILED",
            extra_data={
                "event_id": event_id,
                "user_id": request.user.id,
                "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def deactivate_event(request, event_id):
    try:
        event = Event.objects.get(id=event_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=event.edir,
            status="Active"
        ).only("id").first()
        event.status = "Not Active"
        event.updated_date = timezone.now()
        event.save()
        
        audit_log(
            action="DEACTIVATE_EVENT",
            request=request,
            status="SUCCESS",
            extra_data={
                "event_id":event_id,
                "user_id": maker.id
            },
        )
        return JsonResponse({"message": "Event deactivated successfully"}, status=200)
    except Event.DoesNotExist:
        return JsonResponse({"error": "Event not found"}, status=404)
    except Exception as e:
        audit_log(
            action="DEACTIVATE_EVENT",
            request=request,
            status="FAILED",
            extra_data={
                "event_id": event_id,
                "user_id": request.user.id,
                "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_helps(request):
    try:
        helps = Help.objects.all()
        serializer = HelpSerializer(helps, many=True)
        return Response(serializer.data)
    except Exception as e:
        audit_log(
            action="FETCH_HELP",
            request=request,
            status="FAILED",
            extra_data={
                "user_id": request.user.id,
                "error": str(e)}
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

