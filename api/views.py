from asyncio.log import logger

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
from .serializers import BankSerializer, DepositSerializer, EdirDetailHeaderSerializer, EdirUserDetailSerializer, ExpenseChangeRequestSerializer, FeeChangeRequestSerializer, FamilyWithUserSerializer, EdirSerializer, PaymentChangeRequestSerializer, TransactionSerializer, UserWithEdirsSerializer, EdirDetailSerializer, EdirSerializer, FeeSerializer, FeeAssignmentReadOnlySerializer, ChangePasswordSerializer, FeeAssignmentDetailSerializer, FeeWithAssignmentsSerializer, BankChangeRequestSerializer, EdirUserChangeRequestSerializer
from .serializers import UserDetailSerializer, BankWithEdirSerializer, EdirDetailSerializer, UserWithNumFam2Serializer, EdirSerializer, EdirWithUserStatusSerializer, HelpSerializer, EventSerializer, ExpenseFeeSerializer, FeeDetailSerializer, FeeAssignmentSerializer, EdirChangeRequestSerializer, ExpenseChangeRequestSerializer, ExpenseDetailSerializer, UserWithRoleSerializer, EdirUserWithNumFamSerializer, FamilyChangeRequestSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Deposit, DepositChangeRequest, EdirAuditLog, EdirChangeRequest, EdirUserChangeRequest, ExpenseChangeRequest, FeeAssignmentTrxChangeRequest, FeeChangeRequest, Family, Edir, Fee, FeeAssignment, Bank, EdirUser, Help, Event, Transaction, UserAuditLog, EdirUserAuditLog, BankAuditLog, FeeAuditLog, FeeAssignAuditLog, CustomUser, TrxAuditLog, BankChangeRequest, TransactionChangeRequest, UserChangeRequest, FamilyChangeRequest
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
from django.db.models.functions import TruncDate
from django.db import transaction
from collections import defaultdict
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
import uuid
import json
from rest_framework.parsers import MultiPartParser, FormParser
from django.forms.models import model_to_dict
import logging
from core.audit import model_to_json

import calendar
import datetime
from datetime import date

User = get_user_model()

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])  
def members_list_create(request, edir_id=None):
    try:
        if request.method == 'GET':
            edir = Edir.objects.get(id=edir_id)
            
            edir_users = EdirUser.objects.filter(
                edir=edir,
                status="Active"
            )
            edirSerializer = EdirDetailHeaderSerializer(edir)
            member_serializer = EdirUserDetailSerializer(edir_users, many=True, context={"edir_id": edir.id})
            
            userRequest = EdirUserChangeRequest.objects.filter(edir=edir, status="PENDING")
            userRequestSerializer = EdirUserChangeRequestSerializer(userRequest, many=True)

            serializer = Response({"members":member_serializer.data, "member_requests": userRequestSerializer.data, "edir": edirSerializer.data})

            return Response(serializer.data, status=status.HTTP_200_OK) 

        if request.method == 'POST':
            data = request.data.copy()
            data['edir'] = edir_id 
            serializer = EdirUserWithNumFamSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Edir.DoesNotExist:
        return Response({"error": "Edir not found"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # or your custom permission
def active_members_list(request, edir_id=None):
    try:
        edir = Edir.objects.get(id=edir_id)

        edir_users = EdirUser.objects.filter(
            edir=edir,
            status="Active"
        ).select_related("user")
        # users = [eu.user for eu in edir_users]

        serializer = EdirUserWithNumFamSerializer(edir_users, many=True, context={"edir_id": edir.id})
        return Response(serializer.data, status=status.HTTP_200_OK) 
    except Edir.DoesNotExist:
        return Response({"error": "Edir not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def members_by_edir(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
        
        # members = edir.users.all()
        edir_users = EdirUser.objects.filter(edir=edir, status = "Active")
        data = [{"id": m.id, "name": m.full_name} for m in edir_users]
        return Response(data, status=status.HTTP_200_OK)
    except Edir.DoesNotExist:
        return Response({"error": "Edir not found"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail_with_family(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserDetailSerializer(user)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_detail(request, user_id, edir_id=None):
    
    logger = logging.getLogger("user_registration")
    # current_user = EdirUser.objects.filter(
    #         user=request.user,
    #         edir=edir,
    #         status="Active"
    #     ).only("id").first()
    edir= None
    try:
        user = User.objects.get(id=user_id)
        membership = None
        # membership_status = "Not a Member"
        if edir_id is not None:
            edir = Edir.objects.get(id=edir_id)
            # membership = EdirUser.objects.get(user=user, edir=edir)
            membership = EdirUser.objects.filter(user=user, edir=edir).first()
        else:
            membership = EdirUser.objects.filter(user=user).first()
            # print("membership", membership)

        if request.method == 'GET':
            serializer = EdirUserWithNumFamSerializer(membership)
            # membership = GroupMembership.objects.get(user=user, group__edir_id=edir_id)
            # response_data = serializer.data
            # response_data["is_committee"] = membership.is_committee if membership else False
            # response_data["membership_status"] = membership_status
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif request.method in ['PUT', 'PATCH']:
            serializer = EdirUserWithNumFamSerializer(membership, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                is_committee = request.data.get("is_Committee", None)
                if is_committee is not None:
                    # membership = GroupMembership.objects.filter(user=user, group__edir_id=edir_id).first()
                    membership = EdirUser.objects.filter(user=user, edir=edir).first()
                    if membership:
                        membership.is_committee = bool(is_committee)
                        membership.save()

                # return combined response
                response_data = serializer.data
                if membership:
                    response_data["is_committee"] = membership.is_committee
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except User.DoesNotExist:
        logger.exception(
            f"Fetch user detail failed | user not found | user id = {user_id }"
        )
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    except Edir.DoesNotExist:
        logger.exception(
            f"Fetch user detail failed | edir not found | user id = {user_id}"
        )
        return Response({"detail": "Edir not found"}, status=status.HTTP_404_NOT_FOUND)
    
    except EdirUser.DoesNotExist:
        logger.exception(
            f"Fetch user detail failed | user edir not found | user id = {user_id}"
        )
        return Response({"detail": "EdirUser not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"Fetch user detail failed | user id = {user_id} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def member_detail(request, user_id, edir_id=None):
    
    logger = logging.getLogger("user_registration")
    edir= None
    try:
        user = User.objects.get(id=user_id)
        membership = None
        if edir_id is not None:
            edir = Edir.objects.get(id=edir_id)
            # membership = EdirUser.objects.get(user=user, edir=edir)
            membership = EdirUser.objects.filter(user=user, edir=edir).first()
        else:
            membership = EdirUser.objects.filter(user=user).first()
            print("membership", membership)

        serializer = EdirUserDetailSerializer(membership)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception(
            f"Fetch user detail failed | user id = {user_id} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_member(request, member_id):
    try:
        member = EdirUser.objects.get(id=member_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=member.edir,
            status="Active"
        ).only("id").first()
        EdirUserChangeRequest.objects.create(
            edir_user=member,
            edir=member.edir,
            action="UPDATE",
            old_value= model_to_json(member, exclude=["updated_date"]), 
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        logger.info(
                f"Member update request was recorded successfully it waits approval | new value={request.data} | old value={model_to_json(member, exclude=['updated_date'])} | requested by={request.user}"
            )
        
        return Response(EdirUserWithNumFamSerializer(member).data, status=status.HTTP_201_CREATED)
    except EdirUser.DoesNotExist:
        logger.exception(
            f"Member update failed | Member not found | member={model_to_json(member, exclude=['updated_date']) if 'member' in locals() else 'Unknown'} | updated by={request.user} | error={str(e)}"
        )
        return Response({"error": "Member not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"Member update failed | member={model_to_json(member, exclude=['updated_date']) if 'member' in locals() else 'Unknown'} | updated by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def self_register(request):
    logger = logging.getLogger("user_registration")
    if request.method == 'POST':
        try:
            log_data = request.data.copy()
            log_data.pop("password", None)
            log_data.pop("re_password", None)
            # logger.info("Self registration request received | user data: " + json.dumps(log_data))
            data = request.data  # Use request.data to get JSON payload

            full_name = data.get('full_name')
            phone_number = data.get('phone_number')
            # email = data.get('email')
            # gender = data.get('gender')
            # marital_status = data.get('marital_status')
            # profession = data.get('profession')
            address = data.get('address')
            password = data.get('password')

            if not full_name or not phone_number:
                logger.warning(
                    f"Validation failed - Missing fields | data: {data}"
                )
                return Response({'error': 'full_name and phone_number are required'}, status=status.HTTP_400_BAD_REQUEST)

            user = User.objects.create(
                phone_number=phone_number,
                # email=email,
                # full_name=full_name,
                # gender=gender,
                # marital_status=marital_status,
                # profession=profession,
                # address=address,
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

            logger.info(
                f"User Registered by self successfully | user={user} | added_by={request.user}"
            )
            edir_user = EdirUser.objects.create(
                user=user,
                # edir=edir,
                phone_number = phone_number,
                full_name=full_name,
                # gender=gender,
                # marital_status=marital_status,
                # profession=profession,
                address=address,
                # is_committee=bool(is_committee),
                # status="Active",
                # joined_date=timezone.now(),
            )

            # edir_user = EdirUser.objects.get(user=user, edir=edir)
            # edir_user.is_committee = bool(is_committee)
            # edir_user.save()
            # logger.info(
            #     f"Member added to edir by admin successfully | new_user={edir_user} | edir={edir} | added_by={request.user} | is_committe={is_committee}"
            # )
            # EdirUserChangeRequest.objects.create(
            #     edir_user=edir_user,
            #     action="CREATE",
            #     new_value=request.data,
            #     maker=user,
            #     status="CREATED",
            # )
            # UserAuditLog.objects.create(
            #     user=user,
            #     action="Self Registered",
            #     performed_by=user,
            #     new_value=model_to_dict(user, exclude=["password","last_login", "user_permissions","updated_date"]),
            # )
            logger.info(
                f"User registered successfully | user_data="+ json.dumps(model_to_json(user, exclude=["password","last_login", "updated_date"]))
            )
            return Response({'message': 'Registration successful'})
        except Exception as e:
            logger.exception(
                f"Registration failed | user data = {request.data} | error={str(e)}"
            )

            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@api_view(['POST'])
def admin_create_user(request, edir_id):
    
    logger = logging.getLogger("user_registration")
    try:
        # logger.info(f"User added by admin request received | user ={request.data} | request_from {request.user}")
        data = request.data  # Use request.data to get JSON payload

        full_name = data.get('full_name')
        phone_number = data.get('phone_number')
        gender = data.get('gender')
        marital_status = data.get('marital_status')
        profession = data.get('profession')
        address = data.get('address')
        is_committee = data.get('is_committee', False)

        if not full_name or not phone_number:
            logger.warning(
                f"Validation failed - Missing fields | data: {data}"
            )
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
                    {"error": "First add committee to confirm"},
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

                    logger.info(
                        f"User Created by admin successfully | user={user} | added_by={request.user}"
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
                logger.info(
                    f"Member added to edir by admin successfully | new_user={edir_user} | edir={edir} | added_by={request.user} | is_committe={is_committee}"
                )
                EdirUserChangeRequest.objects.create(
                    edir_user=edir_user,
                    edir=edir,
                    action="CREATE",
                    new_value=request.data,
                    maker=maker,
                    status="CREATED",
                )
        
        else:
            EdirUserChangeRequest.objects.create(
                # user=user_instance,
                edir=edir,
                action="CREATE",
                new_value=request.data,
                phone_number= phone_number,
                status="PENDING",
                maker=maker,
            )

            return Response(
                {"message": "Request sent for approval"},
                status=status.HTTP_201_CREATED
            )

        return Response({'message': 'Member added by admin successfully'}, status=status.HTTP_201_CREATED)

    except Edir.DoesNotExist:
        return Response({'error': 'Edir not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"User Registration failed user={edir_user if 'edir_user' in locals() else 'Unknown'}| added by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def approve_member (request, id):
    logger = logging.getLogger("member")
    try:
        change = EdirUserChangeRequest.objects.get(id=id)
        edir = change.edir
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            logger.exception(
                f"Member create request approval failed because it's already processed | membername={change.new_value.get('full_name')} | rejected by={request.user} "
            )
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

                logger.info(
                    f"User Created by admin successfully | user={user} | added_by={request.user}"
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
            logger.info(
                f"Member added to edir by admin successfully | new_user={edir_user} | edir={edir} | added_by={request.user} | is_committe={is_committee}"
            )
        elif change.action == "UPDATE":
            edir_user.phone_number = phone_number
            edir_user.full_name = full_name
            edir_user.address = address
            edir_user.gender = gender
            edir_user.marital_status = marital_status
            edir_user.profession = profession
            edir_user.is_committee = bool(is_committee)
            edir_user.save()
            logger.info(
                f"Member updated successfully | updated_user={edir_user} | updated_by={request.user}"
            )

        elif change.action == "DISABLE":
            change.comment = data.get("reason")

            edir_user.status = "Not Active"
            edir_user.updated_date = timezone.now()
            edir_user.save()
            logger.info(
            f"User approved edir_user deactivation request successfully | approved_by={request.user.id, request.user.phone_number} | edir_user={change.old_value}"
            )

        # expense = Fee.objects.get(id=expense_id)
        # previous_expense = model_to_json(expense)
        # change.edir_user = edir_user
        change.status = "APPROVED"
        change.approved_at = timezone.now()
        change.checker = checker
        change.save()
        logger.info(
            f"EdirUser creation request approval recorded successfully | approved_by={request.user.id, request.user.phone_number} | edir_user={change.edir_user if 'change' in locals() else 'Unknown'}"
        )

        return JsonResponse({
            "message": "EdirUser request approved successfully",
            "edir_user_id": edir_user.id,
            "status": "Approved",
            "updated_date": edir_user.updated_date,
        }, status=200)
    except Fee.DoesNotExist:
        return JsonResponse({"error": "Member is not found "}, status=404)
    except Exception as e:
        logger.exception(
            f"Member approval failed | member={change.new_value if 'change' in locals() else 'Unknown'} | approved by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def reject_member (request, id):
    logger = logging.getLogger("expense")
    try:
        change = EdirUserChangeRequest.objects.get(id=id)
        reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            logger.exception(
                f"Member change request rejection failed because it's already processed | member={change.new_value} | rejected by={request.user} | error=Already processed"
            )
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        change.status = "Rejected"
        change.approved_at = timezone.now()
        change.checker = checker
        change.comment= reason
        change.save()
        logger.info(
            f"User rejected member change request successfully | rejected_by={request.user.id, request.user.phone_number} | member={change.new_value}"
        )       

        return JsonResponse({
            "message": "Member request rejected successfully",
            "member": change.new_value,
            "status": "Rejected",
            "updated_date": change.approved_at,
        }, status=200)
    except Fee.DoesNotExist:
        return JsonResponse({"error": "Member is not found "}, status=404)
    except Exception as e:
        logger.exception(
            f"Member rejection failed | member_id={change.new_value if 'change' in locals() else 'Unknown'} | rejected by={request.user} | error={str(e)}"
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
        edir_user = EdirUser.objects.get(edir=edir, user=request.user)
        # edir_user = EdirUser.objects.get(user=user, edir=edir)
        edir_user.status = "Pending"
        edir_user.save()

        EdirUser.objects.create(
            user=request.user,
            edir=edir,
            status= "Pending"
        )
        return Response({'message': 'User created by admin'}, status=status.HTTP_201_CREATED)
    except Edir.DoesNotExist:
        return Response({'error': 'Edir not found'}, status=status.HTTP_404_NOT_FOUND)
    
    except EdirUser.DoesNotExist:
        return JsonResponse({"error": "User is not found in Edir Request"}, status=404)


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_edir_request (request, edir_id, status):
    allowed_statuses = ["Active", "Pending", "Rejected", "Cancelled"]
    if status not in allowed_statuses:
        return Response(
            {"error": "Invalid status value"},
            status=400
        )
    try:
        edir = Edir.objects.get(id=edir_id)
    except Edir.DoesNotExist:
        return JsonResponse({"error": "Edir is not found "}, status=404)
    user_id = request.data.get("userId")
    if not user_id:
        return Response({"error": "userId is required"}, status=400)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "User is not found "}, status=404)
    try:
        edir_user = EdirUser.objects.get(edir=edir, user=user)
    except EdirUser.DoesNotExist:
        return JsonResponse({"error": "User is not found in Edir Request"}, status=404)

    edir_user.status = status
    edir_user.updated_date = timezone.now()
    edir_user.save()

    return JsonResponse({
        "message": "Edir request updated successfully",
        "edir_id": edir.id,
        "status": status,
        "updated_date": edir_user.updated_date,
    }, status=200)


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def cancel_edir_request (request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
    except Edir.DoesNotExist:
        return JsonResponse({"error": "Edir is not found "}, status=404)
    try:
        edir_user = EdirUser.objects.get(edir=edir, user=request.user)
    except EdirUser.DoesNotExist:
        return JsonResponse({"error": "User is not found in Edir Request"}, status=404)

    edir_user.status = "Cancelled"
    edir_user.updated_date = timezone.now()
    edir_user.save()

    return JsonResponse({
        "message": "Edir request cancelled successfully",
        "edir_id": edir.id,
        "status": "Cancelled",
        "updated_date": edir_user.updated_date,
    }, status=200)


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def leave_edir (request, edir_id):
    logger = logging.getLogger("edir_creation")
    try:
        edir = Edir.objects.get(id=edir_id)
        edir_user = EdirUser.objects.get(edir=edir, user=request.user)
        reason = request.data.get('reason')

        edir_user.status = "Leaved"
        edir_user.leave_reason = reason
        edir_user.updated_date = timezone.now()
        edir_user.save()
        
        logger.info(
            f"Member leaved the Edir successfully | edir={edir} | member={request.user}"
        )

        return JsonResponse({
            "message": "Edir request cancelled successfully",
            "edir_id": edir.id,
            "status": "Cancelled",
            "updated_date": edir_user.updated_date,
        }, status=200)
    
    except Edir.DoesNotExist:
        logger.exception(
            f"User leaving edir failed. Edir are not found | edir_id={edir_id if 'edir' in locals() else 'Unknown'} | requested by={request.user} | error={str(e)}"
        )
        return JsonResponse({"error": "Edir is not found "}, status=404)
    except EdirUser.DoesNotExist:
        logger.exception(
            f"User leaving edir failed. the user is not a member of edir | edirname={edir.name if 'edir' in locals() else 'Unknown'} | requested by={request.user} | error={str(e)}"
        )
        return JsonResponse({"error": "User is not found in Edir Request"}, status=404)
    except Exception as e:
        logger.exception(
            f"User leaving edir failed | edirname={edir.name if 'edir' in locals() else 'Unknown'} | requested by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def disable_edir(request, edir_id):
    logger = logging.getLogger("edir_creation")
    try:
        edir = Edir.objects.get(id=edir_id)

        # Allow only PUT and PATCH
        if request.method not in ["PUT", "PATCH"]:
            return JsonResponse(
                {"error": "Only PUT or PATCH method allowed"},
                status=405
            )
        EdirChangeRequest.objects.create(
            edir=edir,
            action="DISABLE",
            old_value= model_to_json(edir, exclude=["updated_date", "users", "created_by"]), 
            new_value= request.data,
            maker=request.user,
            status="PENDING",
        )
        logger.info(
                f"Edir disable request was recorded successfully it waits approval | new value={(edir)} | old value={(edir)} | requested by={request.user}"
            )

        return JsonResponse({
            "message": "Edir deactivation request recorded successfully",
            "edir_id": edir.id,
            "status": edir.status,
            "updated_date": edir.updated_date,
        }, status=200)

    except Edir.DoesNotExist:
        logger.exception(
            f"Edir disable request failed | edir not found | edir_id={edir_id if 'edir' in locals() else 'Unknown'} | requested by={request.user} | error={str(e)}"
        )
        return Response({"error": "Edir not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"Edir disable request failed | edir_id={edir_id if 'edir' in locals() else 'Unknown'} | requested by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def approve_bank (request, id):
    logger = logging.getLogger("bank_account")
    try:
        change = BankChangeRequest.objects.get(id=id)
        if change.status != "PENDING":
            logger.exception(
                f"Bank account create request approval failed because it's already processed | edirname={change.edir.name} | rejected by={request.user} "
            )
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
        # print("change request", change.action)
        if change.action == "CREATE":
            bank = Bank.objects.create(
                edir = edir,
                account_name=account_name,
                bank_name=bank_name,
                account_number=account_number,
                # maker = request.user,
                status = "Active", 
                created_date=timezone.now()
            )
            bank.save()
            logger.info(
                f"User approved bank account creation request successfully | approved_by={request.user.id, request.user.phone_number} | bank={bank}"
            )
        elif change.action == "UPDATE":
            bank = change.bank
            # previous_bank = model_to_json(bank)

            bank.account_name = account_name
            bank.account_number = account_number
            bank.bank_name = bank_name
            bank.updated_date = timezone.now()
            bank.save()
            logger.info(
                f"User approved bank account update request successfully | approved_by={request.user.id, request.user.phone_number} | bank={model_to_json(bank)}"
            )
        elif change.action == "DISABLE":
             bank = change.bank
             previous_bank = model_to_json(bank)

             bank.status = "Not Active"
             bank.updated_date = timezone.now()
             bank.save()
             logger.info(
                f"User approved bank account deactivation request successfully | approved_by={request.user.id, request.user.phone_number} | bank={model_to_json(bank)}"
            )
        # bank = Bank.objects.get(id=bank_id)
        # previous_bank = model_to_json(bank)

        change.status = "APPROVED"
        change.approved_at = timezone.now()
        change.checker = checker
        change.save()
        logger.info(
            f"Bank account action approval recorded successfully | approved_by={request.user.id, request.user.phone_number} | bank={model_to_json(bank)}"
        )

        # BankAuditLog.objects.create(
        #     edir=edir,
        #     bank=bank,
        #     action="Approved Bank Account",
        #     performed_by=request.user,
        #     previous_status = "Pending",
        #     new_status="Active",
        #     old_value = change.old_value,
        #     new_value=change.new_value,
        #     )

        return JsonResponse({
            "message": "Bank request aproved successfully",
            # "bank_id": bank.id,
            "status": "Approve",
            "updated_date": bank.updated_date,
        }, status=200)
    except Bank.DoesNotExist:
        return JsonResponse({"error": "Bank is not found "}, status=404)
    except Exception as e:
        logger.exception(
            f"Bank account creation request approving failed | bank={change.new_value if 'change' in locals() else 'Unknown'} | approved by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def reject_bank (request, id):
    logger = logging.getLogger("bank_account")
    try:
        change = BankChangeRequest.objects.get(id=id)
        reason = request.data.get('reason')
        if change.status != "PENDING":
            logger.exception(
                f"Bank change request rejection failed because it's already processed | bankname={change.bank.account_name} | rejected by={request.user} | error=Already processed"
            )
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
        # bank = Bank.objects.get(id=id)
        # previous_bank = model_to_json(bank)

        change.status = "Rejected"
        change.approved_at = timezone.now()
        change.checker = checker
        change.comment = reason
        change.save()
        logger.info(
            f"User rejected bank account creation request successfully | rejected_by={request.user.id, request.user.phone_number} | bank={change.new_value}"
        )

        # BankAuditLog.objects.create(
        #     # bank=bank,
        #     action="Rejected Bank Account",
        #     performed_by=request.user,
        #     previous_status = "Pending",
        #     new_status="Rejected",
        #     comment = request.data.get("reason"),
        #     old_value = change.old_value,
        #     new_value=change.new_value,
        #     )

        return JsonResponse({
            "message": "Bank account creation request rejected successfully",
            # "bank_id": bank.id,
            "status": "Rejected",
            "updated_date": change.approved_at,
        }, status=200)
    except Bank.DoesNotExist:
        return JsonResponse({"error": "Bank is not found "}, status=404)
    except Exception as e:
        logger.exception(
            f"Bank account creation rejecting failed | bank={change.new_value if 'change' in locals() else 'Unknown'} | rejected by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def approve_expense (request, id):
    logger = logging.getLogger("expense")
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
            logger.exception(
                f"Expense create request approval failed because it's already processed | edirname={change.edir.name} | rejected by={request.user} "
            )
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        category=new.get("category")
        amount=new.get("amount")
        supported_member_id=new.get("supported_member")
        # trx_ref = str(uuid.uuid4())[:16]

        supported_member = None
        if supported_member_id and (category == "Funeral Contribution" or category == "Sickness Support"):
            supported_member = EdirUser.objects.get(id=supported_member_id)
        else:
            supported_member = None
        
        if change.action == "CREATE":
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
            expense.save()
            logger.info(
                f"User approved expense creation request successfully | approved_by={request.user.id, request.user.phone_number} | expense={new}"
            )
            
            # FeeAuditLog.objects.create(
            #     fee=expense,
            #     action="Approved Expense",
            #     performed_by=request.user,
            #     previous_status = "Pending",
            #     new_status="Active",
            #     new_value=change.new_value,
            #     )
                
            trx = Transaction.objects.create(
                transaction_type="WITHDRAW",
                amount=amount,
                payment_method="Cash",
                # bank=bank,
                # image=image,
                user= supported_member.user if supported_member else None,
                edir=edir,
                payment_status="Paid"
            )
            trx.save()
            
            trxRequest = TransactionChangeRequest.objects.create(
                edir=edir,
                user = supported_member if supported_member else None,
                trx =trx,
                action="CREATE",
                new_value=new,
                maker=request.user,
                status="APPROVED",
                )
            trxRequest.save()
            logger.info(
                f"Expense Transaction Completed | trx={trx.reference} | trx_type=Withdraw | by={request.user}"
            )
            
            # TrxAuditLog.objects.create(
            #     transaction=trx,
            #     action="CREATE",
            #     performed_by=request.user,
            #     new_status="APPROVED",
            #     new_value=model_to_json(trx),
            #     )
            
            FeeAssignment.objects.create(
                fee=expense, 
                user=supported_member, 
                # maker = request.user, 
                transaction=trx)
            
            logger.info(
                f"Transaction was assigned to expense successfully |trx={trx} fee={new} created by = {request.user.id}, {request.user.phone_number}"
            )
        elif change.action == "UPDATE":

            # FeeAssignment.objects.filter(fee=change.fee).delete()
            # data = request.data
            # edir = Edir.objects.get(id=fee.edir)
            expense=change.fee

            expense.category = category
            expense.name = new.get("name")
            expense.supported_member = supported_member
            expense.amount = amount
            expense.payment_date = new.get("payment_date")
            expense.reason = new.get("reason")
            expense.save()

            
            # fee_assign = FeeAssignment.objects.filter(fee=change.fee).first()  
            # trx = fee_assign.transaction
            # trx.amount=amount
            # trx.save()

            fee_assign = FeeAssignment.objects.select_related('transaction').filter(fee=change.fee).first()

            if fee_assign and fee_assign.transaction:
                fee_assign.transaction.amount = amount
                fee_assign.transaction.save()
            else:
                logger.error("Transaction missing for FeeAssignment")
            
            fee_assign.user=supported_member
            fee_assign.save()
            
        elif change.action == "DISABLE":
            expense=change.fee

            expense.status = "Not Active"
            expense.updated_date = timezone.now()
            expense.save()
            logger.info(
            f"User approved expense deactivation request successfully | approved_by={request.user.id, request.user.full_name} | expense={change.old_value}"
            )
            change.comment = new.get("reason")

        # expense = Fee.objects.get(id=expense_id)
        # previous_expense = model_to_json(expense)
        change.fee = expense
        change.status = "APPROVED"
        change.approved_at = timezone.now()
        change.checker = checker
        change.save()
        logger.info(
            f"Expense creation request approval recorded successfully | approved_by={request.user.id, request.user.phone_number} | expense={new}"
        )
        
        
        # trx = Transaction.objects.filter(
        #         trx__fee_id=expense_id,
        #     ).first()
        # previous_trx = model_to_json(trx)

        # trx.status = "APPROVED"
        # trx.updated_date = timezone.now()
        # trx.checker = request.user
        # trx.save()
        # logger.info(
        #     f"User approved expense trx successfully | approved_by={request.user.id, request.user.full_name} | expense={model_to_json(trx)}"
        # )

        return JsonResponse({
            "message": "Expense request approved successfully",
            # "expense_id": expense.id,
            "status": "Approved",
            "updated_date": expense.updated_date,
        }, status=200)
    except Fee.DoesNotExist:
        return JsonResponse({"error": "Expense is not found "}, status=404)
    except Exception as e:
        logger.exception(
            f"Expense approval failed | expense={change.new_value if 'change' in locals() else 'Unknown'} | approved by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def reject_expense (request, id):
    logger = logging.getLogger("expense")
    try:
        
        change = ExpenseChangeRequest.objects.get(id=id)
        reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            logger.exception(
                f"Expense change request rejection failed because it's already processed | expense={change.new_value} | rejected by={request.user} | error=Already processed"
            )
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        change.status = "Rejected"
        change.approved_at = timezone.now()
        change.checker = checker
        change.comment= reason
        change.save()
        logger.info(
            f"User rejected expense change request successfully | rejected_by={request.user.id, request.user.phone_number} | expense={change.new_value}"
        )       

        return JsonResponse({
            "message": "Expense request rejected successfully",
            "expense": change.new_value,
            "status": "Rejected",
            "updated_date": change.approved_at,
        }, status=200)
    except Fee.DoesNotExist:
        return JsonResponse({"error": "Expense is not found "}, status=404)
    except Exception as e:
        logger.exception(
            f"Expense rejection failed | expense_id={change.new_value if 'change' in locals() else 'Unknown'} | rejected by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def approve_fee (request, id):
    logger = logging.getLogger("fee")
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
            logger.exception(
                f"Fee create request approval failed because it's already processed | edirname={change.edir.name} | rejected by={request.user} "
            )
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        category = new.get("category")
        assign_type = new.get("assign_type")
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
                    logger.exception(
                        f"Fee approval failed | This monthly fee already exists. | expense={change.new_value if 'change' in locals() else 'Unknown'} | approved by={request.user}"
                    )
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

            if assign_type == "All Members":
                # members = edir.users.all()
                members = EdirUser.objects.filter(
                    edir=edir,
                    status="Active"
                )
                for m in members:
                    if supported_member and m == supported_member:
                        continue
                    else:
                        FeeAssignment.objects.create(fee=fee, user=m) #, maker = request.user
                
                assigned_members_info = [
                    {
                        "id": m.id,
                        "phone": m.phone_number
                    }
                    for m in members
                ]
                logger.info(
                    f"fee created for all members successfully | "
                    f"fee={fee} | "
                    f"assigned_members={assigned_members_info} | "
                    f"created_by={request.user.id, request.user.phone_number}"
                )
                
            elif assign_type == "Custom Users":
                user_ids = new.get("users", [])
                for uid in user_ids:
                    user = EdirUser.objects.get(id=uid)
                    if supported_member and user == supported_member:
                        continue
                    else:
                        FeeAssignment.objects.create(fee=fee, user=user)#, maker = request.user
                
                logger.info(
                    f"fee created for custom members successfully | fee={fee} assigned members id = {user_ids} created by = {request.user.id}, {request.user.phone_number}"
                )
            
            
            # FeeAssignment.objects.create(
            #     fee=expense, 
            #     user=supported_member, 
            #     maker = request.user, 
            #     # transaction=trx 
            #     )
            
            # logger.info(
            #     f"Transaction was assigned to expense successfully |trx={trx} fee={new} created by = {request.user.id}, {request.user.phone_number}"
            # )
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
                    fee_assign.status = "Disabled"
                    fee_assign.save()
            for uid in user_ids:
                try:
                    user = EdirUser.objects.get(id=uid)
                    existing_assignment = FeeAssignment.objects.filter(fee=fee, user=user, status="Active").exists()
                    # existing_assignment = FeeAssignment.objects.filter(
                    #     fee=fee,
                    #     user=user
                    # ).filter(
                    #     Q(transaction__isnull=False) | Q(transaction_change_request__status="PENDING")
                    # ).exists()
                    if not existing_assignment:
                        if str(uid) == str(supported_member_id):
                            # FeeAssignment.objects.create(fee=fee, user=user, payment_status="For You")
                            continue
                        else:
                            FeeAssignment.objects.create(fee=fee, user=user)
                except EdirUser.DoesNotExist:
                    continue


            # expense.category = category
            # expense.name = new.get("name")
            # expense.supported_member = supported_member
            # expense.amount = new.get("amount")
            # expense.payment_date = new.get("payment_date")
            # expense.reason = new.get("reason")
            # expense.save()

            
            # fee_assign = FeeAssignment.objects.filter(fee=change.fee).first()  
            # # trx = fee_assign.transaction
            # # trx.amount=amount
            # # trx.save()
            
            # fee_assign.user=supported_member
            # fee_assign.save()
        elif change.action == "DISABLE":
            fee=change.fee

            fee.status = "Not Active"
            fee.updated_date = timezone.now()
            fee.save()
            logger.info(
            f"User approved fee deactivation request successfully | approved_by={request.user.id, request.user.phone_number} | fee={change.old_value}"
            )
            change.comment = new.get("reason")

        # expense = Fee.objects.get(id=expense_id)
        # previous_expense = model_to_json(expense)
        change.fee = fee
        change.status = "APPROVED"
        change.approved_at = timezone.now()
        change.checker = checker
        change.save()
        logger.info(
            f"Fee creation request approval recorded successfully | approved_by={request.user.id, request.user.phone_number} | expense={new}"
        )

        return JsonResponse({
            "message": "Fee request approved successfully",
            # "fee_id": fee.id,
            "status": "Approved",
            "updated_date": fee.updated_date,
        }, status=200)
    except Fee.DoesNotExist:
        return JsonResponse({"error": "Fee is not found "}, status=404)
    
    except User.DoesNotExist:
        return Response(
            {"error": "Supported member not found."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.exception(
            f"Fee approval failed | expense={change.new_value if 'change' in locals() else 'Unknown'} | approved by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Fee approval failed due to Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def reject_fee (request, id):
    logger = logging.getLogger("fee")
    try:
        
        change = FeeChangeRequest.objects.get(id=id)
        reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            logger.exception(
                f"Expense change request rejection failed because it's already processed | expense={change.new_value} | rejected by={request.user} | error=Already processed"
            )
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        # expense = Fee.objects.get(id=expense_id)
        # previous_expense = model_to_json(expense)

        change.status = "Rejected"
        change.approved_at = timezone.now()
        change.checker = checker
        change.comment= reason
        change.save()
        logger.info(
            f"User rejected fee change request successfully | rejected_by={request.user.id, request.user.phone_number} | fee={change.new_value}"
        )

        return JsonResponse({
            "message": "Fee request rejected successfully",
            "expense": change.new_value,
            "status": "Rejected",
            "updated_date": change.approved_at,
        }, status=200)
    except Fee.DoesNotExist:
        return JsonResponse({"error": "Fee is not found "}, status=404)
    except Exception as e:
        logger.exception(
            f"Fee rejection failed | fee_id={change.new_value if 'change' in locals() else 'Unknown'} | rejected by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(['POST'])
def add_existed_user(request, edir_id):
    data = request.data
    phone_number = data.get('phone_number')
    is_committee = data.get('is_Committee', False)

    try:
        user = User.objects.get(phone_number=phone_number)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        edir = Edir.objects.get(id=edir_id)
    except Edir.DoesNotExist:
        return Response({'error': 'Edir not found'}, status=status.HTTP_404_NOT_FOUND)

    # Add user to Edir
    edir.users.add(user)

    # Get or create the related group
    # group, created = CustomGroup.objects.get_or_create(
    #     edir=edir,
    #     name=f"Committee-{edir_id}"
    # )

    # Check if GroupMembership already exists
    # membership, created = GroupMembership.objects.get_or_create(
    #     user=user,
    #     group=group,
    #     defaults={'is_committee': bool(is_committee)}
    # )

    # If it exists but committee status changed, update it
    # if not created and membership.is_committee != bool(is_committee):
    #     membership.is_committee = bool(is_committee)
    #     membership.save()

    return Response({'message': 'User successfully added to Edir'}, status=status.HTTP_201_CREATED)

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
        return Response({
            "status": "error",
            "message": "Edir not found"
        }, status=status.HTTP_404_NOT_FOUND)
    
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

        # Auto-login: create JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Password set successfully",
            "user": {
                "id": user.id,
                # "full_name": user.full_name,
                "phone_number": user.phone_number,
            },
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response(
            {"error": f"Phone {phone_number} does not exist"},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(["POST"])
@permission_classes([AllowAny])   # 👈 allow unauthenticated requests
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


@api_view(['GET'])
@permission_classes([AllowAny])
def check_user_phone(request, phone_number):
    if not phone_number:
        return Response({'detail': 'Phone number is required.'}, status=status.HTTP_400_BAD_REQUEST)

    exists = User.objects.filter(phone_number=phone_number).exists()
    edir_user_exists = EdirUser.objects.filter(phone_number=phone_number).exists()
    return Response({
        "phone_number": phone_number,
        "exists": exists,
        "edir_user_exists": edir_user_exists
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def check_user_phoneNumber(request, phone_number):
    if not phone_number:
        return Response({'detail': 'Phone number is required.'}, status=status.HTTP_400_BAD_REQUEST)

    exists = User.objects.filter(phone_number=phone_number).exists()
    if (exists):
        user = User.objects.get(phone_number=phone_number)
        serializer = UserWithRoleSerializer(user)
        return Response({
        "user": serializer.data,
        "phone_number": phone_number,
        "exists": exists
    }, status=status.HTTP_200_OK)
    return Response({
        "phone_number": phone_number,
        "exists": exists
    }, status=status.HTTP_200_OK)

def set_password(request, user_id):
    if request.method == 'POST':
        user = User.objects.get(id=user_id)
        new_password = request.POST['password']
        user.set_password(new_password)
        user.save()
        return JsonResponse({'message': 'Password set successfully'})


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def deactivate_member(request, member_id):
    # Allow only PUT and PATCH
    if request.method not in ["PUT", "PATCH"]:
        return JsonResponse(
            {"error": "Only PUT or PATCH method allowed"},
            status=405
        )
    try:
        # edir = Edir.objects.get(id = edir_id)
        user = EdirUser.objects.get(id=member_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=user.edir,
            status="Active"
        ).only("id").first()
        # edir_user = EdirUser.objects.get(user=user, edir = edir)

        # edir_user.status = "Not Active"
        # edir_user.updated_date = timezone.now()
        # edir_user.save()
        
        EdirUserChangeRequest.objects.create(
            edir_user=user,
            edir=user.edir,
            action="DISABLE",
            old_value= model_to_json(user, exclude=["updated_date"]), 
            new_value= request.data,
            maker=maker,
            status="PENDING",
        )
        logger.info(
                f"Member disable request was recorded successfully it waits approval | new value={model_to_json(user, exclude=['updated_date'])} | old value={model_to_json(user, exclude=['updated_date'])} | requested by={request.user}"
            )

        return JsonResponse({
            "message": "User deactivated from the Edir successfully",
            "user_id": user.id,
            # "edir_id": edir.id,
            "status": user.status,
            "updated_date": user.updated_date,
        }, status=200)

    except Edir.DoesNotExist:
        return JsonResponse({"error": "Edir not found"}, status=404)

    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    except EdirUser.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

@api_view(['POST'])
def add_family(request, user_id):
    # data = request.data  
    # user = User.objects.get(id=user_id)
    # partner = None
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
            # old_value= model_to_json(edir, exclude=["updated_date", "users"]), # Exclude users to avoid large log entries
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )

        # relationship = data.get('relationship')
        # full_name = data.get('full_name')
        # gender = data.get('gender')
        # # date_of_birth = data.get('date_of_birth')
        # profession = data.get('profession')

        # if not full_name :
        #     return Response({'error': 'full_name is required'}, status=status.HTTP_400_BAD_REQUEST)

        # family = Family.objects.create(
        #     user = user,
        #     # partner= partner_user,
        #     full_name=full_name,
        #     gender=gender,
        #     # date_of_birth=date_of_birth,
        #     profession=profession,
        #     relationship=relationship,
        # )
        # family.save()
        return Response({'message': 'family added by admin'}, status=status.HTTP_201_CREATED)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_family_list(request, user_id):
    try:
        user = EdirUser.objects.get(user_id=user_id)
        family = Family.objects.filter(user=user, status="Active")
        family_serializer = FamilyWithUserSerializer(family, many=True)
        
        family_request = FamilyChangeRequest.objects.filter(edir_user=user, status="PENDING")
        userRequestSerializer = FamilyChangeRequestSerializer(family_request, many=True)

        serializer = Response({"families":family_serializer.data, "family_requests": userRequestSerializer.data})

        return Response(serializer.data)
    except User.DoesNotExist:
        return Response({"detail": "Partner not added"}, status=status.HTTP_404_NOT_FOUND)
    except Family.DoesNotExist:
        return Response({"detail": "Family not added"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def family_detail(request, user_id):
    try:
        family = Family.objects.get(id=user_id)
        # user = EdirUser.objects.get()
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
                # serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Family.DoesNotExist:
        return Response({"detail": "Family not found"}, status=status.HTTP_404_NOT_FOUND)
    

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def deactivate_family(request, family_id):
    # Allow only PUT and PATCH
    if request.method not in ["PUT", "PATCH"]:
        return JsonResponse(
            {"error": "Only PUT or PATCH method allowed"},
            status=405
        )
    try:
        family = Family.objects.get(id=family_id)
        
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=family.user.edir,
            status="Active"
        ).only("id").first()

    # family.status = "Not Active"
    # family.updated_date = timezone.now()
    # family.save()

    
        FamilyChangeRequest.objects.create(
            family=family,
            edir_user=family.user,
            action="DISABLE",
            old_value= model_to_json(family, exclude=["updated_date"]), 
            new_value= request.data,
            maker=maker,
            status="PENDING",
        )
        logger.info(
                f"Member disable request was recorded successfully it waits approval | new value={model_to_json(family, exclude=['updated_date'])} | old value={model_to_json(family, exclude=['updated_date'])} | requested by={request.user}"
            )

        return JsonResponse({
            "message": "Family deactivated successfully",
            "family_id": family.id,
            "status": family.status,
            "updated_date": family.updated_date,
        }, status=200)

    except Family.DoesNotExist:
        return JsonResponse({"error": "Family not found"}, status=404)


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def approve_family(request, id):
    logger = logging.getLogger("member")
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
            logger.exception(
                f"Family create request approval failed because it's already processed | familyname={change.new_value.get('full_name')} | rejected by={request.user} "
            )
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
            logger.info(
                f"Family added approved to user by admin successfully | new_user={edir_user} | added_by={request.user}"
            )
        elif change.action == "UPDATE":

            family.full_name = full_name
            family.gender = gender
            family.relationship = relationship
            family.profession = profession
            family.save()
            logger.info(
                f"Family updated successfully | updated_user={edir_user} | updated_by={request.user}"
            )

        elif change.action == "DISABLE":
            change.comment = data.get("reason")

            family.status = "Not Active"
            family.updated_date = timezone.now()
            family.save()
            logger.info(
            f"User approved family deactivation request successfully | approved_by={request.user.id, request.user.phone_number} | edir_user={change.old_value}"
            )

        change.status = "APPROVED"
        change.approved_at = timezone.now()
        change.checker = checker
        change.save()
        logger.info(
            f"Family creation request approval recorded successfully | approved_by={request.user.id, request.user.phone_number} | family={change.family if 'change' in locals() else 'Unknown'}"
        )

        return JsonResponse({
            "message": "Family request approved successfully",
            # "family_id": family.id,
            "status": "Approved",
            # "updated_date": family.updated_date,
        }, status=200)
    except Fee.DoesNotExist:
        return JsonResponse({"error": "Family is not found "}, status=404)
    except Exception as e:
        logger.exception(
            f"Family approval failed | family={change.new_value if 'change' in locals() else 'Unknown'} | approved by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def reject_family(request, id):
    logger = logging.getLogger("expense")
    try:
        change = FamilyChangeRequest.objects.get(id=id)
        reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir_user.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            logger.exception(
                f"Family change request rejection failed because it's already processed | family={change.new_value} | rejected by={request.user} | error=Already processed"
            )
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        change.status = "Rejected"
        change.approved_at = timezone.now()
        change.checker = checker
        change.comment= reason
        change.save()
        logger.info(
            f"User rejected family change request successfully | rejected_by={request.user.id, request.user.phone_number} | family={change.new_value}"
        )       

        return JsonResponse({
            "message": "Family request rejected successfully",
            "family": change.new_value,
            "status": "Rejected",
            "updated_date": change.approved_at,
        }, status=200)
    except Fee.DoesNotExist:
        return JsonResponse({"error": "Family is not found "}, status=404)
    except Exception as e:
        logger.exception(
            f"Family rejection failed | family={change.new_value if 'change' in locals() else 'Unknown'} | rejected by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_family_member(request, family_id):
    try:
        family_member = Family.objects.get(id=family_id)
        family_member.delete()
        return Response({"message": "Family member deleted successfully"}, status=status.HTTP_200_OK)
    except Family.DoesNotExist:
        return Response({"error": "Family member not found"}, status=status.HTTP_404_NOT_FOUND)
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_edir(request):
    # print("Edir creation request received")
    logger = logging.getLogger("edir_creation")
    try:
        #Create Edir
        data = request.data
        edir_user = None
        serializer = EdirSerializer(data=data)
        if serializer.is_valid():

            edir = serializer.save() #created_by=request.user
            logger.info(
                f"Edir Created by User successfully | edir={data} | created by={request.user}"
            )
            
            maker = EdirUser.objects.filter(
                user=request.user,
                edir=edir,
                status="Active"
            ).only("id").first()
            EdirChangeRequest.objects.create(
                edir=edir,
                action="CREATE",
                new_value=data,
                maker=maker,
                status="CREATED",
            )
            logger.info(
                    f"Edir Creation request was recorded successfully but not need approval for creation | edir={data} | created by={request.user}"
                )
            
            has_no_edir = EdirUser.objects.filter(user=request.user, edir__isnull=True).exists()
            if has_no_edir:
                edir_user = EdirUser.objects.filter(user=request.user, edir__isnull=True).first()
                
                edir_user.edir = edir
                edir_user.is_committee=True
                edir_user.joined_date = timezone.now()

                edir_user.save()
                
                logger.info(
                    f"User added to edir successfully when creating the edir as committee | user={request.user.id, request.user.phone_number} | edir={edir.id, edir.name}"
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
                logger.info(
                    f"User added to edir successfully when creating the edir as committee | user={request.user.id, request.user.phone_number} | edir={edir.id, edir.name}"
                )

            EdirUserChangeRequest.objects.create(
                # user=request.user,
                # edir=edir,
                edir_user=edir_user,
                action="ADD_MEMBER",
                maker=maker,
                new_value=model_to_json(edir_user),
                status="CREATED", 
            )
            logger.info(
                f"User added to edir request recorded successfully when creating the edir as committee but not approval needed | user={request.user.id, request.user.phone_number} | edir={edir.id, edir.name}"
                )

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            # print(serializer.errors)
            logger.exception(
            f"Edir Creation failed | edir name={edir.name if 'edir' in locals() else 'Unknown'} | created by={request.user} | errors={serializer.errors}"
            )
            return Response({'error': 'Bad request error', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception(
            f"Edir Creation failed | edirname={edir.name if 'edir' in locals() else 'Unknown'} | created by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def add_edir(request):
#     serializer = EdirSerializer(data=request.data)
#     if serializer.is_valid():
#         serializer.save(user=request.user)  # 👈 attach logged in user
#         return Response(serializer.data, status=status.HTTP_201_CREATED)
#     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# View all Edirs
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_edirs(request):
    edirs = Edir.objects.all()
    serializer = EdirSerializer(edirs, many=True)
    return Response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_with_edirs(request):
    id = request.query_params.get('id')
    # saved_id = request.data.get('saved_id')
    edirSerializer = None
    # memberSerializer = None
    eventSerializer = None
    edir = None
    # print("edir id = ", id)

    if id is not None:
        is_user_has_edir = EdirUser.objects.filter(
            edir_id=id,
            user=request.user,
            status="Active"
        ).exists()
        # print("user has edir ", is_user_has_edir)

        if is_user_has_edir:
            edir = Edir.objects.filter(id=id).first()
            # print("user selected edir ", edir)

    # if edir is None and saved_id is not None:
    #     is_user_has_saved_edir = EdirUser.objects.filter(
    #         edir_id=saved_id,
    #         user=request.user,
    #         status="Active"
    #     ).exists()

    #     if is_user_has_saved_edir:
    #         edir = Edir.objects.filter(id=saved_id).first()

    if edir is None:
        edir = Edir.objects.filter(
            ediruser__user=request.user,
            ediruser__status="Active"
        ).first()
        # print("system selected edir ", edir)

    if edir is not None:
        edirSerializer = EdirDetailSerializer(edir, context={"request": request})
        # member = EdirUser.objects.filter(
        #     edir=edir,
        #     user=request.user,
        #     status="Active"
        # ).first()
        # memberSerializer = EdirUserWithNumFamSerializer(member)
        
        event = Event.objects.filter(edir=edir, status="Active")
        event = event[:3]
        eventSerializer = EventSerializer(event, many=True)
        
        current_user = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        payments = (
            Transaction.objects.filter(
                feeassignment_trx__user=current_user,
                edir=edir,
            )
            .values(
                "reference",
                "amount",
                "payment_method",
                "created_at",
                "transaction_type",
                "payment_status",
            )
            .filter(
                ~Q(payment_status="Paid") 
            )
            .annotate(
                fee_count=Count("feeassignment_trx", distinct=True)
            )
            .order_by("-created_at")
            .distinct()
        )
        payments = payments[:5]
        
        # print("has edir ", True)
        return Response({"edir": edirSerializer.data, "events": eventSerializer.data, "payments":payments, "has_edir":True})
    else:
        # member = EdirUser.objects.filter(
        #     user=request.user,
        #     status="Active"
        # ).first()
        # memberSerializer = EdirUserWithNumFamSerializer(member)
        # print("has edir ", False)
        return Response({"edir": None, "events": None, "payments":None, "has_edir":False})

    # serializer = EdirSerializer(edir)
    # serializer = UserWithEdirsSerializer(request.user)
    # return Response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_edirs(request):
    # edirs = request.user.edirs.all()
    edirs = Edir.objects.filter(
        ediruser__user=request.user,
        ediruser__status="Active"   # <-- FILTER BY ACTIVE MEMBERSHIP
    )
    serializer = EdirSerializer(edirs, many=True)
    # serializer = UserWithEdirsSerializer(request.user)
    return Response(serializer.data)

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_popular_edirs(request):
#     edirs = Edir.objects.filter(
#         # ediruser__user=request.user,
#         status="Active"   
#     ).exclude(
#         ediruser__user=request.user,
#         ediruser__status__in=["Active", "Pending"]
#     )
#     serializer = EdirSerializer1(edirs, many=True)
#     return Response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_popular_edirs(request):
    excluded_edirs = EdirUser.objects.filter(
        user=request.user,
        status__in=["Active", "Pending"]
    ).values("edir_id")

    edirs = Edir.objects.filter(
        status="Active", is_popular = True
    ).exclude(
        id__in=Subquery(excluded_edirs)
    )

    serializer = EdirSerializer(edirs, many=True)
    return Response(serializer.data)

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_requested_edirs(request):
#     edirs = Edir.objects.filter(
#         ediruser__user=request.user,
#         ediruser__status="Pending" && ediruser__status="Rejected" 
#     )
#     serializer = EdirSerializer1(edirs, many=True)
#     return Response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_requested_edirs(request):
    edirs = Edir.objects.filter(
        ediruser__user=request.user,
        ediruser__status__in=["Pending", "Rejected", "Cancelled"]
    ).distinct()

    serializer = EdirWithUserStatusSerializer(
        edirs,
        many=True,
        context={"request": request}
    )
    return Response(serializer.data)


@api_view(['POST'])
def add_bank(request, edir_id):
    logger = logging.getLogger("bank_account")
    data = request.data  
    try:
        edir = Edir.objects.get(id=edir_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        # bank_name = data.get('bank_name')
        # account_name = data.get('account_name')
        # account_number = data.get('account_number')

        BankChangeRequest.objects.create(
            edir=edir,
            action="CREATE",
            # old_value= model_to_json(edir, exclude=["updated_date", "users"]), # Exclude users to avoid large log entries
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        
        # bank = Bank.objects.create(
        #     edir = edir,
        #     account_name=account_name,
        #     bank_name=bank_name,
        #     account_number=account_number,
        #     maker = request.user,
        #     status = "Pending", 
        #     created_date=timezone.now()
        # )
        # bank.save()
        logger.info(
            f"New Bank account creation request added successfully, needs approval | added_by={request.user.id, request.user.phone_number} | edir_id={edir_id} | bank={request.data}"
        )
        # BankAuditLog.objects.create(
        #     # bank=bank,
        #     action="New Bank Account",
        #     performed_by=request.user,
        #     new_status="Pending",
        #     new_value=request.data,
        #     )
        return Response({'message': 'bank added by admin'}, status=status.HTTP_201_CREATED)

    except Edir.DoesNotExist:
        return Response({'error': 'edir not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"New Bank account creation request adding failed | edir_id={edir_id if 'edir_id' in locals() else 'Unknown'} | created by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def edir_bank_list(request, edir_id):
    logger = logging.getLogger("bank_account")
    try:
        edir = Edir.objects.get(id=edir_id)
        bank = Bank.objects.filter(edir=edir, status__in=["Active", "Pending"])
        
        serializer = BankWithEdirSerializer(bank, many=True)
        # print(serializer.data)
        return Response(serializer.data)
    except Exception as e:
        logger.exception(
            f"Bank account fetching failed | edir_id={edir_id if 'edir_id' in locals() else 'Unknown'} | created by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def edir_active_bank_list(request, edir_id):
    logger = logging.getLogger("bank_account")
    try:
        edir = Edir.objects.get(id=edir_id)
        bank = Bank.objects.filter(edir=edir, status="Active")
        
        serializer = BankWithEdirSerializer(bank, many=True)
        # print(serializer.data)
        return Response(serializer.data)
    except Exception as e:
        logger.exception(
            f"Bank account fetching failed | edir_id={edir_id if 'edir_id' in locals() else 'Unknown'} | created by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_bank_details(request, bank_id):
    logger = logging.getLogger("bank_account")
    try:
        bank = Bank.objects.get(id=bank_id)
        
        transaction_qs = Transaction.objects.filter(
            edir_id=edir_id
        ).order_by("-created_at")
        deposits = (
            Deposit.objects
            .filter(bank=bank)
            .annotate(total_amount=Sum("transactions__amount"))
            # .prefetch_related("deposit")
            .prefetch_related(
                Prefetch("transactions", queryset=transaction_qs)
            )
        )

        serializer = DepositSerializer(deposits, many=True)
        # serializer = BankDetailsSerializer(bank)

        return Response(
            {"deposits": serializer.data,
            "bank": bank},
            status=200
        )
    except Exception as e:
        logger.exception(
            f"bank detail fetching failed | bank={bank if 'bank' in locals() else 'Unknown'} | requested by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Bank not found or failed to fetch bank details'},
            status=status.HTTP_404_NOT_FOUND
        )
    

@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def bank_detail(request, bank_id):
    try:
        bank = Bank.objects.get(id=bank_id)
    except Bank.DoesNotExist:
        return Response({"detail": "Bank not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = BankWithEdirSerializer(bank)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        serializer = BankWithEdirSerializer(bank, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_bank(request, bank_id):
    logger = logging.getLogger("bank_account")
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
            old_value= model_to_json(bank, exclude=["updated_date"]), # Exclude users to avoid large log entries
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        logger.info(
                f"Bank update request was recorded successfully it waits approval | new value={request.data} | old value={model_to_json(bank, exclude=['updated_date'])} | requested by={request.user}"
            )

        # BankAuditLog.objects.create(
        #     bank=bank,
        #     action="MODIFIED",
        #     new_status="PENDING",
        #     performed_by=request.user,
        #     old_value= model_to_json(bank, exclude=["updated_date"]), # Exclude users to avoid large log entries
        #     new_value=request.data,
        # )

        serializer = BankSerializer(bank)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Bank.DoesNotExist:
        logger.exception(
            f"Bank account update failed | bank not found | bankname={bank.account_name if 'bank' in locals() else 'Unknown'} | updated by={request.user} | error={str(e)}"
        )
        return Response({"error": "Bank not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"Bank account update failed | bankname={bank.account_name if 'bank' in locals() else 'Unknown'} | updated by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def deactivate_bank(request, bank_id):
    logger = logging.getLogger("bank_account")
    try:
        bank = Bank.objects.get(id=bank_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=bank.edir,
            status="Active"
        ).only("id").first()
        # Allow only PUT and PATCH
        if request.method not in ["PUT", "PATCH"]:
            return JsonResponse(
                {"error": "Only PUT or PATCH method allowed"},
                status=405
            )
        BankChangeRequest.objects.create(
            bank=bank,
            edir=bank.edir,
            action="DISABLE",
            old_value= model_to_json(bank, exclude=["updated_date"]), 
            new_value= request.data,
            maker=maker,
            status="PENDING",
        )
        logger.info(
                f"Bank disable request was recorded successfully it waits approval | new value={model_to_json(bank, exclude=['updated_date'])} | old value={model_to_json(bank, exclude=['updated_date'])} | requested by={request.user}"
            )

        # bank = Bank.objects.get(id=bank_id)
        
        # bank.status = "Not Active"
        # bank.updated_date = timezone.now()
        # bank.save()
        return JsonResponse({
            "message": "Bank deactivation request recorded successfully",
            "bank_id": bank.id,
            "status": bank.status,
            "updated_date": bank.updated_date,
        }, status=200)

    except Bank.DoesNotExist:
        logger.exception(
            f"Bank account disable request failed | bank not found | bankname={bank.account_name if 'bank' in locals() else 'Unknown'} | updated by={request.user} | error={str(e)}"
        )
        return Response({"error": "Bank not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"Bank account disable request failed | bankname={bank.account_name if 'bank' in locals() else 'Unknown'} | updated by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_bank(request, bank_id):
    try:
        bank = Bank.objects.get(id=bank_id)
        bank.delete()
        return Response({"message": "Bank deleted successfully"}, status=status.HTTP_200_OK)
    except Bank.DoesNotExist:
        return Response({"error": "Bank not found"}, status=status.HTTP_404_NOT_FOUND)


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def disable_fee(request, fee_id):
    logger = logging.getLogger("fee")
    try:
        fee = Fee.objects.get(id=fee_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=fee.edir,
            status="Active"
        ).only("id").first()
        # Allow only PUT and PATCH
        if request.method not in ["PUT", "PATCH"]:
            return JsonResponse(
                {"error": "Only PUT or PATCH method allowed"},
                status=405
            )
        FeeChangeRequest.objects.create(
            fee=fee,
            edir=fee.edir,
            action="DISABLE",
            old_value= model_to_json(fee, exclude=["updated_date"]), 
            new_value= request.data,
            maker=maker,
            status="PENDING",
        )
        logger.info(
                f"Fee disable request was recorded successfully it waits approval | new value={model_to_json(fee, exclude=['updated_date'])} | old value={model_to_json(fee, exclude=['updated_date'])} | requested by={request.user}"
            )

        # bank = Bank.objects.get(id=bank_id)
        
        # bank.status = "Not Active"
        # bank.updated_date = timezone.now()
        # bank.save()
        return JsonResponse({
            "message": "Fee deactivation request recorded successfully",
            "bank_id": fee.id,
            "status": fee.status,
            "updated_date": fee.updated_date,
        }, status=200)

    except Fee.DoesNotExist:
        logger.exception(
            f"Fee disable request failed | fee not found | fee_name={fee.name if 'bank' in locals() else 'Unknown'} | updated by={request.user} | error={str(e)}"
        )
        return Response({"error": "Bank not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"Fee disable request failed | fee={fee.name if 'bank' in locals() else 'Unknown'} | updated by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def disable_expense(request, fee_id):
    logger = logging.getLogger("expense")
    try:
        fee = Fee.objects.get(id=fee_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=fee.edir,
            status="Active"
        ).only("id").first()
        # Allow only PUT and PATCH
        if request.method not in ["PUT", "PATCH"]:
            return JsonResponse(
                {"error": "Only PUT or PATCH method allowed"},
                status=405
            )
        ExpenseChangeRequest.objects.create(
            fee=fee,
            edir=fee.edir,
            action="DISABLE",
            old_value= model_to_json(fee, exclude=["updated_date"]), 
            new_value= request.data,
            maker=maker,
            status="PENDING",
        )
        logger.info(
                f"Expense disable request was recorded successfully it waits approval | new value={model_to_json(fee, exclude=['updated_date'])} | old value={model_to_json(fee, exclude=['updated_date'])} | requested by={request.user}"
            )

        # bank = Bank.objects.get(id=bank_id)
        
        # bank.status = "Not Active"
        # bank.updated_date = timezone.now()
        # bank.save()
        return JsonResponse({
            "message": "Expense deactivation request recorded successfully",
            "bank_id": fee.id,
            "status": fee.status,
            "updated_date": fee.updated_date,
        }, status=200)

    except Fee.DoesNotExist:
        logger.exception(
            f"Expense disable request failed | fee not found | fee_name={fee.name if 'fee' in locals() else 'Unknown'} | updated by={request.user} | error={str(e)}"
        )
        return Response({"error": "Bank not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"Expense disable request failed | fee={fee.name if 'fee' in locals() else 'Unknown'} | updated by={request.user} | error={str(e)}"
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
        return Response({'message': 'Event added by admin'}, status=status.HTTP_201_CREATED)

    except Edir.DoesNotExist:
        return Response({'error': 'edir not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def edir_event_list(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
        event = Event.objects.filter(edir=edir, status="Active")
    except Edir.DoesNotExist:
        return Response({"detail": "Edir not added"}, status=status.HTTP_404_NOT_FOUND)
    except Event.DoesNotExist:
        return Response({"detail": "Event not added"}, status=status.HTTP_404_NOT_FOUND)
    limit = request.query_params.get("limit")
    if limit is not None:
        try:
            limit = int(limit)
            event = event[:limit]
        except ValueError:
            return Response({"error": "Invalid limit"}, status=status.HTTP_400_BAD_REQUEST)

    serializer = EventSerializer(event, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def popular_event_list(request):
    try:
        event = Event.objects.filter(edir__isnull=True, status="Active")
    except Event.DoesNotExist:
        return Response({"detail": "Event not added"}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = EventSerializer(event, many=True)
    return Response(serializer.data)

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def event_detail(request, event_id):
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Response({"detail": "Event not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = EventSerializer(event)
        return Response(serializer.data)
    
    elif request.method == "PUT":
        # print("FILES:", request.FILES)
        # print("DATA:", request.data)
        # print("id:", event_id)
        serializer = EventSerializer(event, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    # elif request.method == "POST" and request.POST.get("_method") == "PUT":
    #     serializer = EventSerializer(
    #         event,
    #         data=request.data,
    #         partial=True
    #     )
    #     serializer.is_valid(raise_exception=True)
    #     serializer.save()
    #     return Response(serializer.data, status=status.HTTP_200_OK)

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def deactivate_event(request, event_id):
    # Allow only PUT and PATCH
    if request.method not in ["PUT", "PATCH"]:
        return JsonResponse(
            {"error": "Only PUT or PATCH method allowed"},
            status=405
        )
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return JsonResponse({"error": "Event not found"}, status=404)

    event.status = "Not Active"
    event.updated_date = timezone.now()
    event.save()

    return JsonResponse({
        "message": "Event deactivated successfully",
        "event_id": event.id,
        "status": event.status,
        "updated_date": event.updated_date,
    }, status=200)

# # Add Payment
# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def add_payment(request):
#     user = request.user
#     edir_id = request.data.get("edirId")
#     edir = Edir.objects.get(id=edir_id)
#     month = request.data.get("month")  
#     amount = request.data.get("amount")

#     if Bill.objects.filter(user=user, edir=edir, month=month).exists():
#         return Response({"detail": "Bill already exists."}, status=status.HTTP_400_BAD_REQUEST)

#     payment = Payment.objects.create(
#         user=user,
#         edir=edir,
#         month=month,
#         amount=amount
#     )

#     serializer = PaymentSerializer(payment)
#     # if serializer.is_valid():
#     # serializer.save()
#     return Response(serializer.data, status=status.HTTP_201_CREATED)
#     # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# View Payments for logged-in user
# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def my_payments(request):
#     payments = Payment.objects.filter(user=request.user).order_by("-payment_date")
#     serializer = PaymentSerializer(payments, many=True)
#     return Response(serializer.data)

# View All Payments (Admin use)
# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def all_payments(request):
#     if not request.user.is_staff:
#         return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
#     payments = Payment.objects.all().order_by("-payment_date")
#     serializer = PaymentSerializer(payments, many=True)
#     return Response(serializer.data)


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def pay_bill(request):

#     reason = request.data.get("reason")
#     method = request.data.get("method")
#     if(method == "cash"):
#         is_paid = True
#     else:
#         is_paid = False
#     payment = Payment.objects.create(
#         method=method,
#         is_paid = is_paid,
#         reason = reason
#         # transaction_id=request.data.get("transactionId", None),
#     )
#     return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def generate_bill(request):
#     payment = None
#     edir = None
#     user= None
#     user_id = request.data.get("user")
#     if user_id == None:
#         user = request.user
#     else:
#         try:
#             user = User.objects.get(id=user_id)
#         except User.DoesNotExist:
#             return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
#     edir_id = request.data.get("edirId")
#     month = request.data.get("month")
#     amount = request.data.get("amount")
#     payment_id = request.data.get("payment_id")
#     transaction_type = request.data.get("transaction_type")
    
#     try:
#         edir = Edir.objects.get(id=edir_id)
#     except Edir.DoesNotExist:
#         return Response({"detail": "Edir not found."}, status=status.HTTP_404_NOT_FOUND)
#     # Check if bill already exists
#     if Bill.objects.filter(user=user, edir=edir, month=month).exists():
#         return Response({"detail": "Bill already exists."}, status=status.HTTP_400_BAD_REQUEST)
    
#     try:
#         payment = Payment.objects.get(id=payment_id)
#     except Payment.DoesNotExist:
#         return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

#     bill = Bill.objects.create(
#         user=user,
#         edir=edir,
#         # is_paid = True,
#         payment=payment,
#         month=month,
#         amount=amount, #edir.monthly_fee,
#         transaction_type = transaction_type,
#     )

#     return Response(BillSerializer(bill).data, status=status.HTTP_201_CREATED)


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def pay_and_generate_bill(request):
#     user = request.user
#     edir_id = request.data.get("edirId")
#     month = request.data.get("month")

#     if not edir_id or not month:
#         return Response({"detail": "edirId and month are required."}, status=status.HTTP_400_BAD_REQUEST)

#     try:
#         edir = Edir.objects.get(id=edir_id)
#     except Edir.DoesNotExist:
#         return Response({"detail": "Edir not found."}, status=status.HTTP_404_NOT_FOUND)

#     # prevent duplicate bill
#     if Bill.objects.filter(user=user, edir=edir, month=month).exists():
#         return Response({"detail": "Bill already exists for this month."}, status=status.HTTP_400_BAD_REQUEST)

#     try:
#         with transaction.atomic():  # ensures all or nothing
#             # Create Payment
#             payment = Payment.objects.create(
#                 user=user,
#                 method=request.data.get("method", "cash"),
#                 transaction_id=str(uuid.uuid4())[:12]  # unique transaction id
#             )

#             # Create Bill
#             bill = Bill.objects.create(
#                 user=user,
#                 edir=edir,
#                 payment=payment,
#                 is_paid=True,
#                 month=month,
#                 amount=edir.monthly_fee,
#             )

#         return Response({
#             "payment": PaymentSerializer(payment).data,
#             "bill": BillSerializer(bill).data
#         }, status=status.HTTP_201_CREATED)

#     except Exception as e:
#         return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def user_bills(request, edir_id):
#     user = request.user
#     edir = Edir.objects.get(id=edir_id)
#     bills = Bill.objects.filter(user=user, edir=edir).order_by("-created_at")
#     serializer = BillSerializer(bills, many=True)
#     return Response(serializer.data)

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def user_payments(request, edir_id):
#     user = request.user
#     # edir = None
#     try:
#         edir = Edir.objects.get(id=edir_id)
#     except Edir.DoesNotExist:
#         return Response({"detail": "Edir not found."}, status=status.HTTP_404_NOT_FOUND)
#     # Group bills by payment id
#     payments = (
#         Bill.objects.filter(user=user, edir = edir)
#         .values(
#             "payment_id",
#             "payment__method",
#             "payment__paid_at",
#             "payment__reason",
#             "transaction_type",
#         )
#         .annotate(
#             number_of_months=Count("month", distinct=True),
#             total_amount=Sum("amount"),
#         )
#         .order_by("-payment__paid_at")
#     )

    # return Response(payments)

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_user_payments(request, user_id, edir_id):
#     try:
#         payments = (
#             FeeAssignment.objects.filter(
#                 user_id=user_id,
#                 fee__edir_id=edir_id,
#                 Trx_ref__isnull=False,
#                 payment_status="Paid",
#             )
#             .values("Trx_ref")  
#             .annotate(
#                 total_amount=Sum("fee__amount"),
#                 method=F("method"),   
#                 paid_date=F("paid_date"), 
#                 transaction_type=F("fee__transaction_type"),
#                 user_id=F("user_id"),
#                 edir_id=F("fee__edir_id"),
#                 fee_count=Count("fee"),
#             )
#             .order_by("-paid_date")
#         )

#         limit = request.query_params.get("limit")
#         if limit is not None:
#             try:
#                 limit = int(limit)
#                 payments = payments[:limit]
#             except ValueError:
#                 return Response({"error": "Invalid limit"}, status=status.HTTP_400_BAD_REQUEST)

#         return Response(payments, status=status.HTTP_200_OK)
#     except Exception as e:
#         return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_user_payments(request, user_id, edir_id):
#     logger = logging.getLogger("fetch_payment")
#     try:
#         payments = (
#             Transaction.objects.filter(
#                 feeAssignment__user_id=user_id,
#                 feeAssignment__fee__edir_id=edir_id,
#             )
#             .values(
#                 "reference",
#                 "amount",
#                 "payment_method",
#                 "created_at",
#                 "transaction_type",
#                 "payment_status",
#             )
#             .annotate(
#                 fee_count=Count("feeAssignment", distinct=True)
#             )
#             .order_by("-created_at")
#             .distinct()
#         )

#         limit = request.query_params.get("limit")
#         if limit:
#             payments = payments[:int(limit)]

#         return Response(payments, status=status.HTTP_200_OK)

#     except Exception as e:
#         logger.exception(
#             f"Fetch Recent Payment Transaction list failed | requested by={request.user} | user_id={user_id} | edir_id={edir_id} | payments={payments} error={str(e)}"
#         )
#         return Response(
#             {"error": "Failed to fetch payments"},
#             status=status.HTTP_400_BAD_REQUEST,
#         )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_payments(request, user_id):
    logger = logging.getLogger("fetch_payment")
    try:
        current_user = EdirUser.objects.get(id=user_id)
        payments = (
            Transaction.objects.filter(
                feeassignment_trx__user=current_user,
                payment_status="PAID",
            )
            .values(
                "reference",
                "amount",
                "payment_method",
                "created_at",
                "transaction_type",
                "payment_status",
            )
            .filter(
                ~Q(payment_status="Paid") 
            )
            .annotate(
                fee_count=Count("feeassignment_trx", distinct=True)
            )
            .order_by("-created_at")
            .distinct()
        )

        limit = request.query_params.get("limit")
        if limit:
            payments = payments[:int(limit)]

        payment_request = TransactionChangeRequest.objects.filter(edir=current_user.edir, user= current_user, status="PENDING")
        paymentRequestSerializer = PaymentChangeRequestSerializer(payment_request, many=True, context={'request': request})

        return Response({"payments": payments, "payment_requests": paymentRequestSerializer.data}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception(
            f"Fetch Recent Payment Transaction list failed | "
            f"requested by={request.user} | user_id={user_id} | error={str(e)}"
        )

        return Response(
            {"error": "Failed to fetch payments"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_undeposited_trxs(request, edir_id):
    logger = logging.getLogger("fetch_payment")
    try:
        edir = Edir.objects.get(id=edir_id)
        # pending_requests = FeeAssignmentTrxChangeRequest.objects.filter(
        #     fee_assignment=OuterRef("pk"),
        #     trx_change_request__status="PENDING"
        # )
        undeposited_trxs = (
            Transaction.objects.filter(
                # fee__edir_id=edir_id,
                payment_method="cash",
                edir=edir,
                deposit__isnull=True
            )
            # .exclude(
            #     feeassignmenttrxchangerequest__trx_change_request__status="PENDING"
            # )
            # .annotate(has_pending=Exists(pending_requests))
            # .filter(has_pending=False)
            .order_by("-id")
            # .select_related("fee")
        )

        data = [
            {
                "id": a.id,
                # "fee_id": a.fee.id,
                # "fee_name": a.fee.name,
                # "category": a.fee.category,
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
        logger.exception(
            f"Fetch Undeposited transactions list failed | "
            f"requested by={request.user} | edir_id={edir_id} | error={str(e)}"
        )

        return Response(
            {"error": "Failed to fetch undeposited transactions list"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_helps(request):
    helps = Help.objects.all()
    serializer = HelpSerializer(helps, many=True)
    return Response(serializer.data)

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_fee_details(request, id):
#     try:
#         fee = Fee.objects.get(id=id)
#     except Fee.DoesNotExist:
#         return Response({"error": "fee not found"}, status=404)

#     serializer = FeeSerializer(fee)
#     return Response(serializer.data)

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_fee_details(request, id):
#     fee = get_object_or_404(Fee, id=id)
#     assignments = FeeAssignment.objects.filter(fee=fee) #.select_related("user")

#     # Build assignment details safely
#     assigned_users = []
#     for a in assignments:
#         if a.user:
#             assigned_users.append({
#                 "user_id": a.user.id,
#                 "full_name": a.user.full_name.strip() if a.user.full_name else "Edir",
#                 "payment_status": a.payment_status,
#                 "paid_date": a.paid_date,
#                 "method": a.method,
#                 "trx_ref": a.Trx_ref,
#             })
#         else:
#             # Handle null user (e.g., Edir or general fee)
#             assigned_users.append({
#                 "user_id": None,
#                 "full_name": "Edir",
#                 "payment_status": a.payment_status,
#                 "paid_date": a.paid_date,
#                 "method": a.method,
#                 "trx_ref": a.Trx_ref,
#             })

#     # Fee details
#     fee_data = {
#         "id": fee.id,
#         "name": fee.name,
#         "reason": fee.reason,
#         "amount": fee.amount,
#         "category": fee.category,
#         "payment_date": fee.payment_date,
#         "edir_id": fee.edir_id,
#         "assigned_users": assigned_users,
#     }

#     return Response(fee_data, status=200)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_fee_details(request, id):
    logger = logging.getLogger("fetch_payment")

    try:
        fee = get_object_or_404(Fee, id=id)

        assignments = (
            FeeAssignment.objects
            .filter(fee=fee, status="Active")
            .select_related("user", "transaction")
        )

        assigned_users = []

        for a in assignments:
            trx = a.transaction

            if trx and trx.payment_status == "APPROVED":
                payment_status = "PAID"
                method = trx.payment_method
                trx_ref = trx.reference
                paid_date = trx.approved_at

            elif trx and trx.payment_status == "PENDING":
                payment_status = "PENDING"
                method = trx.payment_method
                trx_ref = trx.reference
                paid_date = None

            else:
                payment_status = "NOT PAID"
                method = None
                trx_ref = None
                paid_date = None

            assigned_users.append({
                "user_id": a.user.id if a.user else None,
                "full_name": (
                    a.user.full_name.strip()
                    if a.user and a.user.full_name
                    else "Edir"
                ),
                "payment_status": payment_status,
                "paid_date": paid_date.isoformat() if paid_date else None,
                "method": method,
                "trx_ref": str(trx_ref) if trx_ref else None,
            })

        fee_data = {
            "id": fee.id,
            "name": fee.name,
            "reason": fee.reason,
            "amount": fee.amount,
            "category": fee.category,
            "payment_date": fee.payment_date.isoformat() if fee.payment_date else None,
            "edir_id": fee.edir_id,
            "supported_member": {
                "id": fee.supported_member.id,
                "full_name": fee.supported_member.full_name,
            } if fee.supported_member else None,
            "assigned_users": assigned_users,
        }

        return Response(fee_data, status=200)

    except Exception as e:
        logger.exception(
            f"Fetch fee details failed | requested by={request.user} | fee_id={id} | error={str(e)}"
        )
        return Response({"error": "Failed to fetch fee details"}, status=400)
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_payment_detail(request, ref):
    logger = logging.getLogger("fetch_payment")

    try:
        trx = (
            Transaction.objects
            .filter(reference=ref)
            .select_related("bank")
            .prefetch_related("feeassignment_trx__fee")   # ✅ correct relation
            .first()
        )

        if not trx:
            logger.warning(
                f"Payment not found | ref={ref} | requested by={request.user}"
            )
            return Response({"detail": "No payments found."}, status=404)

        data = {
            "ref": str(trx.reference),
            "created_at": trx.created_at,
            "payment_method": trx.payment_method,
            "bank_name": trx.bank.bank_name if trx.bank else None,
            "image": request.build_absolute_uri(trx.image.url)
                if trx.image else None,
            "total_amount": trx.amount,
            "payment_status": trx.payment_status,
            "fees": [
                {
                    "assignment_id": a.id,
                    "fee_id": a.fee.id,
                    "name": a.fee.name,
                    "amount": a.fee.amount,
                    "category": a.fee.category,
                    "supported_member": (
                        a.fee.supported_member.full_name
                        if a.fee.supported_member else None
                    ),
                }
                for a in trx.feeassignment_trx.all()   # ✅ correct reverse relation
            ],
        }
        serializer = TransactionSerializer(trx, context={"request": request})

        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception(
            f"Fetch payment detail failed | ref={ref} | user={request.user} | error={str(e)}"
        )
        return Response(
            {"error": "Failed to fetch payments"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
# @api_view(['DELETE'])
# @permission_classes([IsAuthenticated])
# def delete_bill(request, bill_id):
#     try:
#         bill = Bill.objects.get(id=bill_id)
#         bill.delete()
#         return Response({"message": "BIll deleted successfully"}, status=status.HTTP_200_OK)
#     except Bill.DoesNotExist:
#         return Response({"error": "Bill not found"}, status=status.HTTP_404_NOT_FOUND)

# @api_view(['DELETE'])
# @permission_classes([IsAuthenticated])
# def delete_payment(request, payment_id):
#     try:
#         payment = Payment.objects.get(id=payment_id)
        
#         # delete related bills first
#         # Bill.objects.filter(payment=payment).delete()
        
#         # then delete payment
#         payment.delete()
#         return {"status": "success", "message": "Payment and related bills deleted"}
#     except Payment.DoesNotExist:
#         return {"status": "error", "message": "Payment not found"}

# @api_view(["DELETE"])
# def delete_payment(request, payment_id):
#     try:
#         payment = Payment.objects.get(id=payment_id)
#         payment.delete()  # cascades to related Bills because of on_delete=models.CASCADE
#         return Response(
#             {"message": "Payment and related bills deleted successfully."},
#             status=status.HTTP_200_OK
#         )
#     except Payment.DoesNotExist:
#         return Response(
#             {"error": "Payment not found."},
#             status=status.HTTP_404_NOT_FOUND
#         )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request, edir_id):
    logger = logging.getLogger("edir_creation")
    try:
        edir = Edir.objects.get(id=edir_id)
        serializer = EdirDetailSerializer(edir, context={"request": request})
            
        # data = serializer.data
        # data["member_count"] = edir.users.count()
        # data["unpaid_months"] = unpaid.count() 
        return Response(serializer.data)
    except Edir.DoesNotExist:
        logger.exception(
            f"Edir detail fetching failed | edir not found | edirname={edir.name if 'edir' in locals() else 'Unknown'} | requested by={request.user} | error={str(e)}"
        )
        return Response({"error": "Edir not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"Edir detail fetching failed | edirname={edir.name if 'edir' in locals() else 'Unknown'} | requested by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def edir_detail(request, edir_id):
    logger = logging.getLogger("edir_creation")
    try:
        edir = Edir.objects.get(id=edir_id)
        edirSerializer = EdirSerializer(edir)
        
        bank = Bank.objects.filter(edir=edir, status="Active")
        bankSerializer = BankWithEdirSerializer(bank, many=True)

        changeRequest = EdirChangeRequest.objects.filter(edir=edir, status="PENDING")
        changeRequestSerializer = EdirChangeRequestSerializer(changeRequest, many=True)

        bankRequest = BankChangeRequest.objects.filter(edir=edir, status="PENDING")
        bankRequestSerializer = BankChangeRequestSerializer(bankRequest, many=True)
        # data = serializer.data
        # data["member_count"] = edir.users.count()
        # data["unpaid_months"] = unpaid.count() 
        return Response({"edir": edirSerializer.data, "banks": bankSerializer.data, "change_requests": changeRequestSerializer.data, "bank_change_requests": bankRequestSerializer.data})
    except Edir.DoesNotExist:
        logger.exception(
            f"Edir detail fetching failed | edir not found | edirname={edir.name if 'edir' in locals() else 'Unknown'} | requested by={request.user} | error={str(e)}"
        )
        return Response({"error": "Edir not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"Edir detail fetching failed | edirname={edir.name if 'edir' in locals() else 'Unknown'} | requested by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_edir(request, edir_id):
    logger = logging.getLogger("edir_creation")
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
            old_value= model_to_json(edir, exclude=["updated_date", "users"]), # Exclude users to avoid large log entries
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        logger.info(
                f"Edir update request was recorded successfully it waits approval | new value={request.data} | old value={model_to_json(edir, exclude=['updated_date', 'users'])} | requested by={request.user}"
            )

        # EdirAuditLog.objects.create(
        #     edir=edir,
        #     action="MODIFIED",
        #     new_status="PENDING",
        #     performed_by=request.user,
        #     old_value= model_to_json(edir, exclude=["updated_date", "users"]), # Exclude users to avoid large log entries
        #     new_value=request.data,
        # )

        serializer = EdirSerializer(edir)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Edir.DoesNotExist:
        logger.exception(
            f"Edir Update failed | edir not found | edirname={edir.name if 'edir' in locals() else 'Unknown'} | updated by={request.user} | error={str(e)}"
        )
        return Response({"error": "Edir not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"Edir Update failed | edirname={edir.name if 'edir' in locals() else 'Unknown'} | updated by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def approve_edir_edit(request, id):
    logger = logging.getLogger("edir_creation")
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
            logger.exception(
                f"Edir change request rejection failed because it's already processed | edirname={change.edir.name} | rejected by={request.user} | error={str(e)}"
            )
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if change.action == "UPDATE":
            edir.name = new.get("name")
            edir.monthly_fee = new.get("monthly_fee")
            edir.address = new.get("address")
            edir.description = new.get("description")
            # edir.meeting_place = new.get("meeting_place")
            edir.updated_date = timezone.now()

            edir.save()
            logger.info(
                    f"Edir update request was approved successfully | new value={change.new_value} | old value={change.old_value} | requested by={request.user}"
                )
        elif change.action == "DISABLE":

            edir.status = "Not Active"
            edir.updated_date = timezone.now()
            edir.save()
            logger.info(
            f"User approved edir account deactivation request successfully | approved_by={request.user.id, request.user.phone_number} | edir={change.old_value}"
            )
            change.comment = new.get("reason")

        change.status = "APPROVED"
        change.checker = checker
        change.approved_at = timezone.now()
        change.save()
        logger.info(
                f"Edir update request approval was recorded successfully | new value={change.new_value} | old value={change.old_value} | requested by={request.user}"
            )
        
        # EdirAuditLog.objects.create(
        #     edir=edir,
        #     action="MODIFIED",
        #     previous_status=change.status,
        #     new_status="APPROVED",
        #     performed_by=request.user,
        #     old_value= model_to_json(edir, exclude=["updated_date", "users"]), # Exclude users to avoid large log entries
        #     new_value=change.new_value,
        # )

        return Response(
            {"message": "Approved successfully"},
            status=status.HTTP_200_OK
        )

    # except EdirChangeRequest.DoesNotExist:
    #     return Response(
    #         {"error": "Change request not found"},
    #         status=status.HTTP_404_NOT_FOUND
    #     )
    except Exception as e:
        logger.exception(
            f"Edir Update request approval failed | edirname={edir.name if 'edir' in locals() else 'Unknown'} | tried by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def reject_edir_edit(request, id):
    logger = logging.getLogger("edir_creation")
    try:
        change = EdirChangeRequest.objects.get(id=id)
        reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            logger.exception(
                f"Edir change request rejection failed because it's already processed | edirname={change.edir.name} | rejected by={request.user} | error={str(e)}"
            )
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        edir = change.edir
        # new = change.new_value

        # edir.name = new.get("name")
        # edir.monthly_fee = new.get("monthly_fee")
        # edir.address = new.get("address")
        # edir.description = new.get("description")
        # edir.meeting_place = new.get("meeting_place")

        # edir.save()

        change.status = "REJECTED"
        change.checker = checker
        change.comment = reason
        change.approved_at = timezone.now()
        change.save()
        
        logger.info(
                f"Edir update request was rejected successfully | new value={change.new_value} | old value={change.old_value} | requested by={request.user}"
            )
        # EdirAuditLog.objects.create(
        #     edir=edir,
        #     action="MODIFIED",
        #     previous_status=change.status,
        #     new_status="REJECTED",
        #     performed_by=request.user,
        #     old_value= model_to_json(edir, exclude=["updated_date", "users"]), # Exclude users to avoid large log entries
        #     new_value=change.new_value,
        #     comment=reason,
        # )

        return Response(
            {"message": "Rejected successfully"},
            status=status.HTTP_200_OK
        )

    # except EdirChangeRequest.DoesNotExist:
    #     return Response(
    #         {"error": "Change request not found"},
    #         status=status.HTTP_404_NOT_FOUND
    #     )
    except Exception as e:
        logger.exception(
            f"Edir change request rejection failed | edirname={edir.name if 'edir' in locals() else 'Unknown'} | rejected by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def edir_details(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
        serializer = EdirDetailHeaderSerializer(edir, context={"request": request})

    except Edir.DoesNotExist:
        return Response({"error": "Edir not found."},status=status.HTTP_404_NOT_FOUND)
    return Response(serializer.data)


# @api_view(["GET"])
# def bill_summary(request):
#     transaction_type = request.query_params.get("transaction_type")
#     edir_id = request.query_params.get("edir_id")

#     if not transaction_type or not edir_id:
#         return Response({"error": "transaction_type and edir_id are required"}, status=400)

#     bills = (
#         Bill.objects.filter(transaction_type=transaction_type, edir_id=edir_id)
#         .values("payment_date__date")   # group by date only
#         .annotate(total_amount=Sum("amount"))
#         .order_by("payment_date__date")
#     )

#     # Convert queryset dict to serializer-compatible format
#     data = [
#         {"payment_date": item["payment_date__date"], "total_amount": item["total_amount"]}
#         for item in bills
#     ]

#     serializer = BillSummarySerializer(data, many=True)
#     return Response(serializer.data)

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_withdrawals(request, edir_id):
#     withdrawals = FeeAssignment.objects.filter(
#         fee__transaction_type="Withdrawal",
#         fee__edir_id=edir_id
#     ).select_related("fee", "user")

#     serializer = WithdrawalSerializer(withdrawals, many=True)
#     return Response(serializer.data, status=200)

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_edir_expenses(request, edir_id):
#     try:
#         fees = Fee.objects.filter(edir_id=edir_id, transaction_type="Withdraw").order_by("-id")

#         # if not fees.exists():
#         #     return Response({"error": "No withdrawals found for this edir"}, status=404)

#         limit = request.query_params.get("limit")
#         if limit is not None:
#             try:
#                 limit = int(limit)
#                 fees = fees[:limit]
#             except ValueError:
#                 return Response({"error": "Invalid limit"}, status=status.HTTP_400_BAD_REQUEST)
#         serializer = FeeWithAssignmentsSerializer(fees, many=True)
#         return Response(serializer.data, status=200)

#     except Exception as e:
#         return Response({"error": str(e)}, status=400)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_edir_expenses(request, edir_id):
    logger = logging.getLogger("fetch_payment")
    try:
        expenses = Fee.objects.filter(
                fee_type="Expense",
                edir_id=edir_id,
                status__in=["Active","Completed"]   
            )
        expense_serializer = FeeDetailSerializer(expenses, many=True)
        
        expenseRequest = ExpenseChangeRequest.objects.filter(edir_id=edir_id, status="PENDING")
        expenseRequestSerializer = ExpenseChangeRequestSerializer(expenseRequest, many=True)

        # print(expenses)  # Debug: print the generated SQL query
        # limit = request.query_params.get("limit")
        # if limit:
        #     try:
        #         expenses = expenses[:int(limit)]
        #     except ValueError:
        #         return Response(
        #             {"error": "Invalid limit"},
        #             status=status.HTTP_400_BAD_REQUEST,
        #         )
        serializer = Response({"expenses":expense_serializer.data, "expense_requests": expenseRequestSerializer.data})
        # serializer = ExpenseFeeSerializer(expenses, many=True)
        return Response(serializer.data, status=200)
    except Exception as e:
        logger.exception(
            f"Fetch expenses list failed | "
            f"requested by={request.user} | "
            f"edir_id={edir_id} | error={str(e)}"
        )

        return Response(
            {"error": "Failed to fetch expenses list"},
            status=status.HTTP_400_BAD_REQUEST,
        )

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_deposit_details(request, edir_id):
    
#     payment_method = request.query_params.get("payment_method")
#     payment_date = request.query_params.get("payment_method")
#     # edir_id = request.query_params.get("edir_id")
#     try:
#         fees = FeeAssignment.objects.filter(fee__edir_id=edir_id, method=payment_method, paid_date = payment_date, payment_status = "paid")

#         if not fees.exists():
#             return Response({"error": "No withdrawals found for this edir"}, status=404)

#         serializer = FeeAssignmentsSerializer(fees, many=True)
#         return Response(serializer.data, status=200)

#     except Exception as e:
#         return Response({"error": str(e)}, status=400)

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_deposit_details(request, edir_id):
#     payment_method = request.query_params.get("method")
#     payment_date_str = request.query_params.get("payment_date")

#     date_obj = parse_date(payment_date_str) if payment_date_str else None

#     try:
#         fees = Transaction.objects.filter(
#             trx__fee__edir_id=edir_id,
#             method=payment_method,
#             payment_status="Paid",
#             transaction_type="PAYMENT",
#             **({"created_at__date": date_obj} if date_obj else {})
#         ).select_related("fee", "user")

#         if not fees.exists():
#             return Response({"error": "No deposits found for this edir"}, status=404)

#         # Group by user full name
#         grouped = defaultdict(lambda: {
#             "full_name": None,
#             "method": None,
#             "total_amount": Decimal("0.00"),
#             "fees": []
#         })

#         for fee in fees:
#             user_name = fee.user.full_name if fee.user else "Unknown"
#             grouped[user_name]["full_name"] = user_name
#             grouped[user_name]["method"] = payment_method
#             grouped[user_name]["total_amount"] += fee.fee.amount
#             grouped[user_name]["fees"].append({
#                 "fee_name": fee.fee.name,
#                 "fee_category": fee.fee.category,
#                 "amount": str(fee.fee.amount),
#             })

#         # response = {
#         #     "paid_date": str(date_obj) if date_obj else None,
#         #     "data": list(grouped.values())
#         # }

#         result = list(grouped.values())

#         # Convert Decimal to string
#         for item in result:
#             item["total_amount"] = str(item["total_amount"])

#         return Response(result, status=200)

#         # Convert Decimal to string
#         # for item in response["data"]:
#         #     item["total_amount"] = str(item["total_amount"])

#         # return Response(response, status=200)

#     except Exception as e:
#         return Response({"error": str(e)}, status=400)

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_daily_incomes_details(request, edir_id):

#     payment_method = request.query_params.get("method")
#     payment_date_str = request.query_params.get("payment_date")
#     date_obj = parse_date(payment_date_str) if payment_date_str else None

#     filters = {
#         "trx__fee__edir_id": edir_id,
#         "transaction_type": "PAYMENT",
#         "payment_status__in": ["APPROVED", "PENDING"],
#     }

#     if payment_method:
#         filters["payment_method"] = payment_method

#     if date_obj:
#         filters["created_at__date"] = date_obj

#     transactions = (
#         Transaction.objects
#         .filter(**filters)
#         .select_related("trx__fee", "trx__user")
#         .annotate(total_amount=Sum("amount"))
#     )

#     if not transactions.exists():
#         return Response(
#             {"error": "No deposits found for this edir"},
#             status=status.HTTP_404_NOT_FOUND,
#         )

#     grouped = defaultdict(lambda: {
#         "full_name": None,
#         "method": None,
#         "total_amount": Decimal("0.00"),
#         "fees": []
#     })

#     for trx in transactions:
#         user = trx.trx.user
#         fee = trx.trx.fee

#         user_name = user.full_name if user else "Unknown"

#         grouped[user_name]["full_name"] = user_name
#         grouped[user_name]["method"] = trx.payment_method
#         grouped[user_name]["total_amount"] += trx.amount
#         grouped[user_name]["fees"].append({
#             "fee_name": fee.name,
#             "fee_category": fee.category,
#             "amount": str(trx.amount),
#         })

#     result = list(grouped.values())

#     # Convert Decimal to string
#     for item in result:
#         item["total_amount"] = str(item["total_amount"])

#     return Response(result, status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_daily_incomes_details(request, edir_id):
    logger = logging.getLogger("fetch_payment")
    try:
        payment_method = request.query_params.get("method")
        payment_date_str = request.query_params.get("payment_date")
        date_obj = parse_date(payment_date_str) if payment_date_str else None

        filters = {
            "fee__edir_id": edir_id,
            "transaction__transaction_type": "PAYMENT",
            "transaction__payment_status__in": ["APPROVED", "PENDING"],
        }

        if payment_method:
            filters["transaction__payment_method"] = payment_method

        if date_obj:
            filters["transaction__created_at__date"] = date_obj

        assignments = (
            FeeAssignment.objects
            .filter(**filters)
            .select_related("user", "fee", "transaction")
        )

        if not assignments.exists():
            return Response(
                {"error": "No transactions found"},
                status=status.HTTP_404_NOT_FOUND
            )

        users_group = defaultdict(lambda: {
            "full_name": None,
            "total_amount": Decimal("0.00"),
            "fees": []
        })

        total_amount = Decimal("0.00")

        for assign in assignments:
            user = assign.user
            fee = assign.fee
            trx = assign.transaction

            amount = trx.amount
            total_amount += amount

            user_name = user.full_name if user else "Unknown"

            users_group[user_name]["full_name"] = user_name
            users_group[user_name]["total_amount"] += amount

            users_group[user_name]["fees"].append({
                "name": fee.name,
                "category": fee.category,
                "supported_member": fee.supported_member.full_name if fee.supported_member else None,
                "amount": str(amount)
            })

        users = list(users_group.values())

        for u in users:
            u["total_amount"] = str(u["total_amount"])

        response = {
            "payment_date": str(date_obj),
            "payment_method": payment_method,
            "total_amount": str(total_amount),
            "users": users
        }

        return Response(response, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.exception(
            f"Fetch daily Edir income details failed | "
            f"requested by={request.user} | payment_method={payment_method} | payment_date={payment_date_str} | "
            f"edir_id={edir_id} | error={str(e)}"
        )

        return Response(
            {"error": "Failed to fetch daily edir income details"},
            status=status.HTTP_400_BAD_REQUEST,
        )
# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_edir_incomes(request, edir_id):
#     # deposits = (
#     #     FeeAssignment.objects.filter(
#     #         # fee__transaction_type="Deposit",
#     #         payment_status="Paid",
#     #         fee__edir_id=edir_id
#     #     )
#     #     .annotate(paid_day=TruncDate("paid_date"))  # group by date only
#     #     .values("paid_day", "method")
#     #     .annotate(total_amount=Sum("fee__amount"))
#     #     .order_by("-paid_day")
#     # )
#     paid_trx = Transaction.objects.filter(
#         feeAssignment=OuterRef("pk"),
#         payment_status=["APPROVED"],
#     )

#     paid_fees = (
#         FeeAssignment.objects.filter(
#             fee__edir_id=edir_id,
#             fee__status="Active",
#             trx__transaction_type="PAYMENT",
#         )
#         .annotate(has_payment=Exists(paid_trx))
#         # .filter(has_payment=False)
#         .order_by("-id")
#     )

#     limit = request.query_params.get("limit")
#     if limit is not None:
#         try:
#             limit = int(limit)
#             paid_fees = paid_fees[:limit]
#         except ValueError:
#             return Response({"error": "Invalid limit"}, status=status.HTTP_400_BAD_REQUEST)
#     return Response(paid_fees, status=200)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_edir_incomes(request, edir_id):

    paid_trx = Transaction.objects.filter(
        trx=OuterRef("pk"),
        payment_status__in=["APPROVED", "PENDING"],  # include pending if you want to show them as well
        transaction_type="PAYMENT",
    )

    paid_fees = (
        FeeAssignment.objects.filter(
            fee__edir_id=edir_id,
            fee__status="Active",
        )
        .annotate(has_payment=Exists(paid_trx))
        .filter(has_payment=True)
        .select_related("fee", "user")  # optimize
        .order_by("-id")
    )

    limit = request.query_params.get("limit")
    if limit is not None:
        try:
            paid_fees = paid_fees[:int(limit)]
        except ValueError:
            return Response(
                {"error": "Invalid limit"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    serializer = FeeAssignmentSerializer(paid_fees, many=True)
    return Response(serializer.data, status=200)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_deposits_with_transactions(request, edir_id):
    logger = logging.getLogger("fetch_payment")
    try:
        transaction_qs = Transaction.objects.filter(
            edir_id=edir_id
        ).order_by("-created_at")
        deposits = (
            Deposit.objects
            .filter(transactions__edir_id=edir_id)
            .annotate(total_amount=Sum("transactions__amount"))
            # .prefetch_related("deposit")
            .prefetch_related(
                Prefetch("transactions", queryset=transaction_qs)
            )
            .order_by("-created_at")
        )
        undeposited_trxs = (
            Transaction.objects.filter(
                # fee__edir_id=edir_id,
                payment_method="cash",
                edir_id=edir_id,
                deposit__isnull=True
            )
            .prefetch_related("feeassignment_trx__fee")
            .order_by("-id")
        )
        undeposited_data = [
            {
                "id": a.id,
                "amount": a.amount,
                "user": {
                    "id": a.user.id,
                    "full_name": a.user.full_name,
                } if a.user else None,
                "payment_date": a.created_at.isoformat(),
                "fees": [
                {
                    "id": fee_assignment.fee.id,
                    "name": fee_assignment.fee.name,
                    "amount": fee_assignment.fee.amount,
                    "category": fee_assignment.fee.category,
                }
                for fee_assignment in a.feeassignment_trx.all()
            ],
            }
            for a in undeposited_trxs
        ]

        serializer = DepositSerializer(deposits, many=True)
        return Response({"deposits": serializer.data, "undeposited": undeposited_data})

    except Exception as e:
        logger.exception(
            f"Fetch daily Edir incomes list failed | "
            f"requested by={request.user} | "
            f"edir_id={edir_id} | error={str(e)}"
        )

        return Response(
            {"error": "Failed to fetch daily edir incomes list"},
            status=status.HTTP_400_BAD_REQUEST,
        )

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_expense_detail(request, fee_id):
#     try:
#         fee = Fee.objects.get(id=fee_id)
#         assignment = FeeAssignment.objects.get(fee=fee)

#         serializer = FeeAssignmentDetailSerializer(assignment)
#         return Response(serializer.data, status=200)

#     except FeeAssignment.DoesNotExist:
#         return Response({"error": "Fee assignment not found"}, status=404)
#     except Exception as e:
#         return Response({"error": str(e)}, status=400)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_expense_detail(request, fee_id):
    logger = logging.getLogger("fee")
    try:
        fee = Fee.objects.get(id=fee_id)

        # assignments = (
        #     FeeAssignment.objects
        #     .filter(fee=fee)
        #     .select_related("fee__supported_member", "transaction")
        # )

        serializer = ExpenseDetailSerializer(fee)

        return Response(
            serializer.data,
            # {
            # "fee_id": fee.id,
            # "fee_name": fee.name or "-",
            # "category": fee.category,
            # "amount": fee.amount,
            # "reason": fee.reason,
            # "supported_member": {
            #     "id": fee.supported_member.id,
            #     "full_name": fee.supported_member.full_name,
            # } if fee.supported_member else None,
            # "created_date": fee.created_date,
            # "status": fee.status,
            #   },  
            status=200
        )
    except Exception as e:
        logger.exception(
            f"expense detail fetching failed | fee={fee if 'fee' in locals() else 'Unknown'} | requested by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Fee not found or failed to fetch expense details'},
            status=status.HTTP_404_NOT_FOUND
        )
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_fee_detail(request, fee_id):
    logger = logging.getLogger("fee")
    try:
        fee = Fee.objects.get(id=fee_id)
        assign_users = (
            FeeAssignment.objects
            .filter(fee=fee, status="Active")
            .select_related("user", "transaction")
            # .select_related("fee__supported_member", "transaction")
        )

        serializer = FeeDetailSerializer(fee)

        return Response(
            {"fee": serializer.data,
            "assigned_users": [
                {
                    "id": a.user.id,
                    "full_name": a.user.full_name,
                    "payment_status": a.transaction.payment_status if a.transaction else None,
                    # "transaction_request_status": (
                    #     a.transaction_change_request.status
                    #     if a.transaction_change_request else None
                    # ),
                }
                for a in assign_users
            ]},
            status=200
        )
    except Exception as e:
        logger.exception(
            f"fee detail fetching failed | fee={fee if 'fee' in locals() else 'Unknown'} | requested by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Fee not found or failed to fetch fee details'},
            status=status.HTTP_404_NOT_FOUND
        )
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_fee_request_detail(request, id):
    logger = logging.getLogger("fee")
    try:
        fee = FeeChangeRequest.objects.get(id=id)
        serializer = FeeChangeRequestSerializer(fee)

        return Response(serializer.data, status=200)
    except Exception as e:
        logger.exception(
            f"fee request detail fetching failed | fee request={fee if 'fee' in locals() else 'Unknown'} | requested by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Fee request not found or failed to fetch fee request details'},
            status=status.HTTP_404_NOT_FOUND
        )


    
# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def edir_payments(request):
#     payment_date = request.query_params.get("payment_date")
#     edir_id = request.query_params.get("edir_id")
#     type = request.query_params.get("type")
#     # user = request.user
#     # edir = None
#     try:
#         edir = Edir.objects.get(id=edir_id)
#     except Edir.DoesNotExist:
#         return Response({"detail": "Edir not found."}, status=status.HTTP_404_NOT_FOUND)
#     # Group bills by payment id
#     payments = (
#         Bill.objects.filter(payment_date__date=payment_date, edir = edir, transaction_type= type)
#         .values(
#             "payment_id",
#             "payment__method",
#             "payment__paid_at",
#             "user__full_name",
#             "payment__reason",
#             "transaction_type",
#         )
#         .annotate(
#             number_of_months=Count("month", distinct=True),
#             total_amount=Sum("amount"),
#         )
#     )

#     return Response(payments)

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_meeting_date(request, pk):
    try:
        edir = Edir.objects.get(id=pk)
        edir.meeting_date = request.data.get("meeting_date")
        edir.meeting_place = request.data.get("meeting_place")
        edir.save()
        return Response({"message": "Meeting date updated"}, status=200)
    except Edir.DoesNotExist:
        return Response({"error": "Edir not found"}, status=404)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_fee(request, edir_id):
    logger = logging.getLogger("fee")
    data = request.data
    try:
        # logger.info(f"Create fee request received | fee ={request.data} | edir_id={edir_id} | request_from {request.user}")
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
            # print(exists)
            if exists:
                return Response(
                    {
                        "month_year": "This monthly fee already exists."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # assign_type = data.get("assign_type")
        # category = data.get("category")
        # supported_member_id = data.get("supportedMember")

        # supported_member = None
        # if supported_member_id and (category == "Funeral Contribution" or category == "Sickness Support"):
        #     supported_member = User.objects.get(id=supported_member_id)
        
        FeeChangeRequest.objects.create(
            edir=edir,
            action="CREATE",
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        logger.info(
            f"New fee creation request added successfully, needs approval | created_by={request.user.id, request.user.phone_number} | edir_id={edir_id} | expense={request.data}"
        )


        # fee = Fee.objects.create(
        #     edir=edir,
        #     category=data.get("category"),
        #     name=data.get("name"),
        #     supported_member = supported_member,
        #     # maker = request.user,
        #     reason=data.get("reason"),
        #     amount=data.get("amount"),
        #     payment_date=data.get("payment_date"),
        # )

        # if assign_type == "All Members":
        #     # members = edir.users.all()
        #     members = User.objects.filter(
        #         ediruser__edir=edir,
        #         ediruser__status="Active"
        #     )
        #     for m in members:
        #         if supported_member and m == supported_member:
        #             # FeeAssignment.objects.create(fee=fee, user=m, payment_status="For You")
        #             continue
        #         else:
        #             FeeAssignment.objects.create(fee=fee, user=m) #, maker = request.user
            
        #     assigned_members_info = [
        #         {
        #             "id": m.id,
        #             "phone": m.phone_number
        #         }
        #         for m in members
        #     ]
        #     logger.info(
        #         f"fee created for all members successfully | "
        #         f"fee={fee} | "
        #         f"assigned_members={assigned_members_info} | "
        #         f"created_by={request.user.id, request.user.phone_number}"
        #     )
        #     FeeAuditLog.objects.create(
        #         fee=fee,
        #         action="Create Fee",
        #         performed_by=request.user,
        #         new_value= {
        #             "fee": model_to_dict(fee),
        #             "assigned_members": assigned_members_info,
        #             "created_by": {
        #                 "id": request.user.id,
        #                 "phone_number": request.user.phone_number,
        #             }
        #         },
        #         )

        # elif assign_type == "Custom Users":
        #     user_ids = data.get("users", [])
        #     for uid in user_ids:
        #         user = User.objects.get(id=uid)
        #         if supported_member and user == supported_member:
        #             continue
        #         else:
        #             FeeAssignment.objects.create(fee=fee, user=user)#, maker = request.user
        #     FeeAuditLog.objects.create(
        #         fee=fee,
        #         action="Create Fee",
        #         performed_by=request.user,
        #         new_value= {
        #             "fee": model_to_dict(fee),
        #             "assigned_members": model_to_dict(user_ids),
        #             "created_by": {
        #                 "id": request.user.id,
        #                 "phone_number": request.user.phone_number,
        #             }
        #         },
        #         )
        #     logger.info(
        #         f"fee created for custom members successfully | fee={fee} assigned members id = {user_ids} created by = {request.user.id}, {request.user.phone_number}"
        #     )

        return Response(request.data, status=status.HTTP_201_CREATED)
    except Edir.DoesNotExist:
        return Response(
            {"error": "Edir not found."},
            status=status.HTTP_404_NOT_FOUND,
            )
    except Exception as e:
        logger.exception(
            f"Fee creation failed | fee={request.data if 'request' in locals() else 'Unknown'} | created by={request.user} | error={str(e)}"
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
        FeeChangeRequest.objects.create(
            fee=fee,
            edir=fee.edir,
            action="UPDATE",
            old_value= old_value,
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        logger.info(
                f"Fee update request was recorded successfully it waits approval | new value={request.data} | old value={model_to_json(fee, exclude=['updated_date'])} | requested by={request.user}"
            )
        
        return Response(FeeSerializer(fee).data, status=status.HTTP_201_CREATED)
    except Fee.DoesNotExist:
        logger.exception(
            f"Fee update failed | fee not found | fee={model_to_json(fee, exclude=['updated_date']) if 'fee' in locals() else 'Unknown'} | updated by={request.user} | error={str(e)}"
        )
        return Response({"error": "Bank not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"Fee update failed | fee={model_to_json(fee, exclude=['updated_date']) if 'fee' in locals() else 'Unknown'} | updated by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    # try:
    #     fee = Fee.objects.get(id=fee_id)
    #     # FeeAssignment.objects.filter(fee=fee, payment_status="Not Paid").delete()
    #     # FeeAssignment.objects.filter(fee=fee, payment_status="For You").delete()

        
        # data = request.data
        # name = data.get("name")
        # category=data.get("category")
        # supported_member_id=data.get("supported_member_id")
        # if category == "Monthly Fee":
        #     exists = Fee.objects.filter(
        #         edir=fee.edir,
        #         category="Monthly Fee",
        #         name=name,
        #         status="Active",
        #     ).exclude(id=fee.id).exists()

        #     if exists:
        #         return Response(
        #             {"month_year": "This monthly fee already exists."},
        #             status=status.HTTP_400_BAD_REQUEST,
        #         )
        
        # supported_member = None
        # if supported_member_id and (category == "Funeral Contribution" or category == "Sickness Support"):
        #     supported_member = User.objects.get(id=supported_member_id)
        # else:
        #     supported_member = None

        # update fee fields
    #     fee.category = data.get("category", fee.category)
    #     fee.name = data.get("name", fee.name)
    #     fee.reason = data.get("reason", fee.reason)
    #     fee.amount = data.get("amount", fee.amount)
    #     fee.payment_date = data.get("payment_date", fee.payment_date)
    #     fee.supported_member = supported_member
    #     fee.save()

    #     user_ids = data.get("users", [])
    #     existing_assignments = FeeAssignment.objects.filter(fee=fee)
    #     for fee_assign in existing_assignments:
    #         if str(fee_assign.user.id) not in user_ids:
    #             fee_assign.status = "Disabled"
    #             fee_assign.save()
    #     for uid in user_ids:
    #         try:
    #             user = User.objects.get(id=uid)
    #             existing_assignment = FeeAssignment.objects.filter(fee=fee, user=user, status="Active").exists()
    #             # existing_assignment = FeeAssignment.objects.filter(
    #             #     fee=fee,
    #             #     user=user
    #             # ).filter(
    #             #     Q(transaction__isnull=False) | Q(transaction_change_request__status="PENDING")
    #             # ).exists()
    #             if not existing_assignment:
    #                 if str(uid) == str(supported_member_id):
    #                     # FeeAssignment.objects.create(fee=fee, user=user, payment_status="For You")
    #                     continue
    #                 else:
    #                     FeeAssignment.objects.create(fee=fee, user=user)
    #         except User.DoesNotExist:
    #             continue

    #     return Response(FeeSerializer(fee).data, status=status.HTTP_200_OK)
    # except Fee.DoesNotExist:
    #     return Response({"error": "Fee not found"}, status=status.HTTP_404_NOT_FOUND)
    # except Exception as e:
    #     return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_expense(request, edir_id):
    logger = logging.getLogger("expense")
    try:
        # data = request.data
        # logger.info(f"Create fee request received | fee ={request.data} | edir_id={edir_id} | request_from {request.user}")
        edir = Edir.objects.get(id=edir_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        ExpenseChangeRequest.objects.create(
            edir=edir,
            action="CREATE",
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        logger.info(
            f"New expense creation request added successfully, needs approval | created_by={request.user.id, request.user.phone_number} | edir_id={edir_id} | expense={request.data}"
        )
        
        # FeeAuditLog.objects.create(
        #     # fee=fee,
        #     action="Create Fee",
        #     performed_by=request.user,
        #     new_status="PENDING",
        #     new_value= request.data,
        # )

        return Response(request.data, status=status.HTTP_201_CREATED)
   
    except Exception as e:
        logger.exception(
            f"Expense creation failed | fee={request.data} | created by={request.user} | error={str(e)}"
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
        ExpenseChangeRequest.objects.create(
            fee=fee,
            edir=fee.edir,
            action="UPDATE",
            old_value= model_to_json(fee, exclude=["updated_date"]), # Exclude users to avoid large log entries
            new_value=request.data,
            maker=maker,
            status="PENDING",
        )
        logger.info(
                f"Expense update request was recorded successfully it waits approval | new value={request.data} | old value={model_to_json(fee, exclude=['updated_date'])} | requested by={request.user}"
            )
        
        return Response(FeeSerializer(fee).data, status=status.HTTP_201_CREATED)
    except Fee.DoesNotExist:
        logger.exception(
            f"Expense update failed | Expense not found | expense={model_to_json(fee, exclude=['updated_date']) if 'fee' in locals() else 'Unknown'} | updated by={request.user} | error={str(e)}"
        )
        return Response({"error": "Bank not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"Expense update failed | expense={model_to_json(fee, exclude=['updated_date']) if 'fee' in locals() else 'Unknown'} | updated by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_edir_fees(request, edir_id):
    logger = logging.getLogger("fetch_payment")
    try:
        edir = Edir.objects.get(id=edir_id)

        # fees = (
        #     Fee.objects.filter(
        #         edir=edir,
        #         status="Active",
        #         assignments__transaction__transaction_type="PAYMENT"
        #     )
        #     .order_by("-id")
        #     .distinct()
        # )
        fees =  Fee.objects.filter(
                edir=edir,
                status="Active",
                fee_type="Income",
            )

        fee_serializer = FeeDetailSerializer(fees, many=True)
        
        feeRequest = FeeChangeRequest.objects.filter(edir_id=edir_id, status="PENDING")
        feeRequestSerializer = FeeChangeRequestSerializer(feeRequest, many=True)


        # limit = request.query_params.get("limit")
        # if limit:
        #     try:
        #         fees = fees[:int(limit)]
        #     except ValueError:
        #         return Response(
        #             {"error": "Invalid limit"},
        #             status=status.HTTP_400_BAD_REQUEST,
        #         )

        # serializer = FeeSerializer(fees, many=True)
        serializer = Response({"fees":fee_serializer.data, "fee_requests": feeRequestSerializer.data})
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception(
            f"Fetch Edir Fees list failed | "
            f"requested by={request.user} | "
            f"edir_id={edir_id} | error={str(e)}"
        )

        return Response(
            {"error": "Failed to fetch edir fees list"},
            status=status.HTTP_400_BAD_REQUEST,
        )


# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_edir_fees(request, edir_id):
#     logger = logging.getLogger("fetch_payment")
#     try:
#         expenses = (
#             Transaction.objects.filter(
#                 transaction_type="PAYMENT",
#                 trx__fee__edir_id=edir_id   # ✅ via FeeAssignment
#             )
#             .select_related("maker", "bank")
#             # .prefetch_related("trx__fee")
#             .prefetch_related(
#                 "trx",
#                 "trx__fee",
#                 "trx__fee__supported_member"
#             )
#             .order_by("-id")
#             .distinct()
#         )
#         print(expenses)  # Debug: print the generated SQL query
#         # limit = request.query_params.get("limit")
#         # if limit:
#         #     try:
#         #         expenses = expenses[:int(limit)]
#         #     except ValueError:
#         #         return Response(
#         #             {"error": "Invalid limit"},
#         #             status=status.HTTP_400_BAD_REQUEST,
#         #         )

#         serializer = ExpenseFeeSerializer(expenses, many=True)
#         return Response(serializer.data, status=200)
#     except Exception as e:
#         logger.exception(
#             f"Fetch fees list failed | "
#             f"requested by={request.user} | "
#             f"edir_id={edir_id} | error={str(e)}"
#         )

#         return Response(
#             {"error": "Failed to fetch expenses list"},
#             status=status.HTTP_400_BAD_REQUEST,
#         )

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_unpaid_fees(request, edir_id, user_id):
#     try:
#         # Filter unpaid fees
#         unpaid_fees = FeeAssignment.objects.filter(
#             fee__edir_id=edir_id,
#             fee__status="Active",
#             user_id=user_id,
#             payment_status="Not Paid"
#         ).order_by("-id")

#         serializer = FeeAssignmentReadOnlySerializer(unpaid_fees, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)

#     except Exception as e:
#         return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_unpaid_fees(request, edir_id, user_id):
#     try:

#         # ✅ check transactions linked via ManyToMany
#         paid_or_pending_trx = Transaction.objects.filter(
#             feeAssignment__id=OuterRef("pk"),
#             payment_status__in=["APPROVED", "PENDING"],
#         )

#         unpaid_fees = (
#             FeeAssignment.objects.filter(
#                 fee__edir_id=edir_id,
#                 fee__status="Active",
#                 user_id=user_id,
#             )
#             .annotate(has_payment=Exists(paid_or_pending_trx))
#             .filter(has_payment=False)
#             .order_by("-id")
#             .select_related("fee", "fee__supported_member")
#         )

#         data = [
#             {
#                 "id": a.id,  # ⭐ include assignment id (important for payment)
#                 "fee_id": a.fee.id,
#                 "fee_name": a.fee.name,
#                 "category": a.fee.category,
#                 "amount": a.fee.amount,
#                 "supported_member": {
#                     "id": a.fee.supported_member.id,
#                     "full_name": a.fee.supported_member.full_name,
#                 } if a.fee.supported_member else None,
#                 "payment_date": a.fee.payment_date,
#             }
#             for a in unpaid_fees
#         ]

#         return Response(data, status=status.HTTP_200_OK)

#     except Exception as e:
#         print(str(e))
#         return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_unpaid_fees(request, user_id):
    logger = logging.getLogger("fetch_payment")
    try:
        user = EdirUser.objects.get(id=user_id)
        pending_requests = FeeAssignmentTrxChangeRequest.objects.filter(
            fee_assignment=OuterRef("pk"),
            trx_change_request__status="PENDING"
        )
        unpaid_fees = (
            FeeAssignment.objects.filter(
                # fee__edir_id=edir_id,
                status="Active",
                user=user,
                transaction__isnull=True
            )
            # .exclude(
            #     feeassignmenttrxchangerequest__trx_change_request__status="PENDING"
            # )
            .annotate(has_pending=Exists(pending_requests))
            .filter(has_pending=False)
            .order_by("-id")
            .select_related("fee")
        )

        data = [
            {
                "id": a.id,
                "fee_id": a.fee.id,
                "fee_name": a.fee.name,
                "category": a.fee.category,
                "amount": a.fee.amount,
                "supported_member": {
                    "id": a.fee.supported_member.id,
                    "full_name": a.fee.supported_member.full_name,
                } if a.fee.supported_member else None,
                "payment_date": a.fee.payment_date,
            }
            for a in unpaid_fees
        ]

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception(
            f"Fetch Unpaid Fees list failed | "
            f"requested by={request.user} | user_id={user_id} | error={str(e)}"
        )

        return Response(
            {"error": "Failed to unpaid fees list"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_paid_fees(request, ref):
    try:
        # Filter unpaid fees
        trx = Transaction.objects.get(reference=ref)
        paid_fees = FeeAssignment.objects.filter(transaction=trx)

        serializer = FeeAssignmentReadOnlySerializer(paid_fees, many=True)
        
        # data = [
        #     {
        #         "id": a.id,
        #         "fee_id": a.fee.id,
        #         "fee_name": a.fee.name,
        #         "category": a.fee.category,
        #         "amount": a.fee.amount,
        #         "supported_member": {
        #             "id": a.fee.supported_member.id,
        #             "full_name": a.fee.supported_member.full_name,
        #         } if a.fee.supported_member else None,
        #         "payment_date": a.fee.payment_date,
        #         "payment_method": a.transaction.payment_method if a.transaction else None,
        #     }
        #     for a in paid_fees
        # ]

        return Response({"fees": serializer.data,
        "payment_method": trx.payment_method if trx else None,
        "bank": trx.bank.id if trx and trx.bank else None,
        "image": request.build_absolute_uri(trx.image.url) if trx.image else None
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def pay_fees(request):
#     try:
#         fee_ids = request.data.get("fees", [])  # list of FeeAssignment IDs
#         if not fee_ids:
#             return Response({"error": "No fees selected."}, status=status.HTTP_400_BAD_REQUEST)

#         # Generate one trx_ref for this payment batch
#         trx_ref = str(uuid.uuid4())[:12]  # short unique string

#         # Update selected fees
#         updated_count = FeeAssignment.objects.filter(
#             id__in=fee_ids.id,
#             payment_status="Not Paid"
#         ).update(
#             payment_status="Paid",
#             paid_date=timezone.now(),
#             method="cash",
#             Trx_ref=trx_ref
#         )

#         return Response({
#             "message": f"{updated_count} fees paid successfully.",
#             "trx_ref": trx_ref
#         }, status=status.HTTP_200_OK)

#     except Exception as e:
#         return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# @api_view(["PUT"])
# @permission_classes([IsAuthenticated])
# def admin_pay_fees(request):
#     fees = request.data.get("fees", [])
#     trx_ref = request.data.get("trx_ref")
#     paid_date = request.data.get("paid_date")
#     bank_id = request.data.get("bank")
#     image = request.FILES.get("image")
#     method = request.data.get("method")

#     fees_data = request.data.get("fees", "[]")
#     try:
#         fees = json.loads(fees_data)
#     except json.JSONDecodeError:
#         fees = []

#     try:
#         bank = Bank.objects.get(id=bank_id)
#     except Bank.DoesNotExist:
#         return Response({"error": "Bank not found"}, status=status.HTTP_404_NOT_FOUND)

#     # Extract IDs safely from the list
#     fee_ids = [fee.get("id") for fee in fees if "id" in fee]
#     # Generate one trx_ref for this payment batch
#     if not trx_ref:
#         trx_ref = str(uuid.uuid4())[:12]  # short unique string
#     if paid_date:
#         # parse string to datetime
#         paid_date = parse_datetime(paid_date)
#     if not paid_date:
#         paid_date = timezone.now()
#     updated_count = FeeAssignment.objects.filter(
#         id__in=fee_ids,
#         payment_status="Not Paid"
#     ).update(
#         payment_status="Paid",
#         paid_date=paid_date,
#         method=method,
#         Trx_ref= trx_ref,
#         bank=bank, 
#         image= image
#     )

#     return Response({"updated_count": updated_count}, status=status.HTTP_200_OK)

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def admin_pay_fees(request, edir_id):
    # trx_ref = request.data.get("trx_ref")
    # paid_date = request.data.get("paid_date")
    # bank_id = request.data.get("bank")
    # image = request.FILES.get("image")
    # print(request.data)
    user_id = request.data.get("userId")
    total_amount = request.data.get("total_amount")
    method = request.data.get("method")
    fees_data = request.data.get("fees", [])
    fees_data = json.loads(fees_data) if isinstance(fees_data, str) else fees_data
    # ref= request.data.get("ref")
    data = {
        "fees": fees_data,
        "bank": request.data.get("bank"),
        "total_amount": request.data.get("total_amount"),
        "method": request.data.get("method"),
    }
    try:
        edir = Edir.objects.get(id=edir_id)
        member = EdirUser.objects.get(id=user_id)
        # trx = Transaction.objects.filter(reference=ref).first()
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        
        trx = Transaction.objects.create(
            transaction_type="PAYMENT",
            amount=total_amount,
            payment_method=method,
            edir=edir,
            user=member,
            payment_status="PAID"
        )
        trx_request = TransactionChangeRequest.objects.create(
            edir=edir,
            user=member,
            trx=trx,
            action="CREATE",
            new_value=data,
            maker=maker,
            status="PAID",
        )
        for fee in fees_data:
            fee_assignment = FeeAssignment.objects.filter(
                fee_id=fee,
                user=member,
                status="Active",
                transaction__isnull=True
            ).first()

            if fee_assignment:
                FeeAssignmentTrxChangeRequest.objects.create(
                    fee_assignment=fee_assignment,
                    trx_change_request=trx_request,
                )
        fee_ids = [f["id"] for f in fees_data] if isinstance(fees_data, str) else fees_data
        
        for fee_id in fee_ids:
            fee_assign = FeeAssignment.objects.get(fee_id=fee_id, user = member, transaction__isnull=True)
            fee_assign.updated_date = timezone.now()
            fee_assign.transaction = trx
            fee_assign.save()   
        return Response({'message': 'cash payment added by committee member'}, status=status.HTTP_201_CREATED)
    
    except Edir.DoesNotExist:
        return Response({'error': 'edir not found'}, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.exception(
            f"transaction creation failed | trx={request.data} | created by={request.user} | error={str(e)}"
        )
        return Response(
            {"error": "Internal server error"},
            status=500,
        )


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def deposit_payments(request, edir_id):
    
    # user_id = request.data.get("userId")
    # total_amount = request.data.get("total_amount")
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
        # member = EdirUser.objects.get(id=user_id)
        maker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        
        bank = Bank.objects.filter(id=bank_id)
        
        deposit = Deposit.objects.create(
            transaction_type="PAYMENT",
            payment_method="CASH",
            bank_id=bank_id,
            image=image,
            user=maker,
            # payment_status="PAID"
        )
        deposit_request = DepositChangeRequest.objects.create(
            edir=edir,
            deposit=deposit,
            action="CREATE",
            new_value=data,
            maker=maker,
            status="PAID",
        )
        for cash in cashes_data:
            trx = Transaction.objects.get(id=cash)
            trx.updated_date = timezone.now()
            trx.deposit = deposit
            trx.save()
        return Response({'message': 'cash deposited by committee member'}, status=status.HTTP_201_CREATED)
    
    except Edir.DoesNotExist:
        return Response({'error': 'edir not found'}, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.exception(
            f"cash deposit failed | trx={request.data} | created by={request.user} | error={str(e)}"
        )
        return Response(
            {"error": "Internal server error"},
            status=500,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pay_fees(request, edir_id):
    logger = logging.getLogger("make_payment")

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
    # data = request.data.copy()
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
            # fee_id = fee.get("id")

            fee_assignment = FeeAssignment.objects.filter(
                fee_id=fee,
                user=user,
                status="Active",
                transaction__isnull=True
            ).first()

            if fee_assignment:
                FeeAssignmentTrxChangeRequest.objects.create(
                    fee_assignment=fee_assignment,
                    trx_change_request=trx_request,
                )

        return Response({'message': 'transfer trx added by user'}, status=status.HTTP_201_CREATED)

    #     fees_data = request.data.get("fees", "[]")
    #     bank_id = request.data.get("bank")
    #     user_id = request.data.get("userId")
    #     total_amount = request.data.get("total_amount")
    #     method = request.data.get("method")
    #     image = request.FILES.get("image")

    #     # parse fees
    #     try:
    #         fees = json.loads(fees_data)
    #     except Exception:
    #         logger.error(
    #             f"Failed to parse fees | fees_data={fees_data} | request_from={request.user}"
    #         )
    #         return Response({"error": "Invalid fees"}, status=400)

    #     fee_ids = [f.get("id") for f in fees if f.get("id")]

    #     # validate bank
    #     bank = Bank.objects.filter(id=bank_id).first()
    #     edir= Edir.objects.get(id=edir_id)
    #     user = CustomUser.objects.get(id=user_id)

    #     assignments = FeeAssignment.objects.filter(
    #         fee_id__in=fee_ids,
    #         user=user,
    #         transaction__isnull=True   # ✅ prevent double payment
    #     )

    #     if not assignments.exists():
    #         return Response({"error": "No unpaid fees found"}, status=400)

    #     # ✅ create ONE transaction
    #     trx = Transaction.objects.create(
    #         transaction_type="PAYMENT",
    #         amount=total_amount,
    #         payment_method=method,
    #         edir=edir,
    #         bank=bank,
    #         image=image,
    #         maker=request.user,
    #         payment_status="PENDING"
    #     )

    #     # ✅ link all assignments to this transaction
    #     assignments.update(transaction=trx)

    #     logger.info(
    #         f"Payment created | trx={trx.reference} | assignments={assignments.count()} | by={request.user}"
    #     )
    #     TrxAuditLog.objects.create(
    #         transaction=trx,
    #         action="TRX_CREATED",
    #         performed_by=request.user,
    #         new_status="Pending",
    #         new_value=model_to_json(trx),
    #         )

        # return Response(
        #     {
        #         "transaction_id": trx.id,
        #         "reference": trx.reference,
        #         # "paid_fees": assignments.count(),
        #     },
        #     status=201,
        # )
    
    except Edir.DoesNotExist:
        return Response({'error': 'edir not found'}, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.exception(
            f"transaction creation failed | trx={request.data} | created by={request.user} | error={str(e)}"
        )
        return Response(
            {"error": "Internal server error"},
            status=500,
        )
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_pay_fees(request, edir_id):
    logger = logging.getLogger("make_payment")

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
    # data = request.data.copy()
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
            # fee_id = fee.get("id")

            fee_assignment = FeeAssignment.objects.filter(
                fee_id=fee,
                user=user,
                status="Active",
                # transaction__isnull=True
            ).first()

            if fee_assignment:
                FeeAssignmentTrxChangeRequest.objects.create(
                    fee_assignment=fee_assignment,
                    trx_change_request=trx_request,
                )

        return Response({'message': 'transfer trx updated by user'}, status=status.HTTP_201_CREATED)
    except Edir.DoesNotExist:
        return Response({'error': 'edir not found'}, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.exception(
            f"transaction update request failed | trx={request.data} | created by={request.user} | error={str(e)}"
        )
        return Response(
            {"error": "Internal server error"},
            status=500,
        )


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def disable_payment(request, ref):
    logger = logging.getLogger("fee")
    try:
        # trx = Transaction.objects.get(id=ref)
        
        trx = (
            Transaction.objects
            .filter(reference=ref)
            .select_related("bank")
            .prefetch_related("feeassignment_trx__fee")   # ✅ correct relation
            .first()
        )

        if not trx:
            logger.warning(
                f"Payment not found | ref={ref} | requested by={request.user}"
            )
            return Response({"detail": "No payments found."}, status=404)

        maker = EdirUser.objects.filter(
            user=request.user,
            edir=trx.edir,
            status="Active"
        ).only("id").first()
        # Allow only PUT and PATCH
        if request.method not in ["PUT", "PATCH"]:
            return JsonResponse(
                {"error": "Only PUT or PATCH method allowed"},
                status=405
            )

        data = {
            "fees": [
                str(a.fee.id)
                for a in trx.feeassignment_trx.all()   
            ],
            "bank": trx.bank.id if trx.bank else None,
            "total_amount": trx.amount,
            "method": trx.payment_method,
        }

        trx_request = TransactionChangeRequest.objects.create(
            trx=trx,
            user=trx.user,
            edir=trx.edir,
            action="DISABLE",
            old_value= data, 
            new_value= request.data,
            maker=maker,
            status="PENDING",
            image=trx.image,
        )
        logger.info(
                f"Payment disable request was recorded successfully it waits approval | new value={model_to_json(trx, exclude=['updated_date'])} | old value={model_to_json(trx, exclude=['updated_date'])} | requested by={request.user}"
            )
        
        
        for fee in data["fees"]:
            fee_assignment = FeeAssignment.objects.filter(
                fee_id=fee,
                user=trx.user,
                status="Active",
                # transaction__isnull=True
            ).first()

            if fee_assignment:
                FeeAssignmentTrxChangeRequest.objects.create(
                    fee_assignment=fee_assignment,
                    trx_change_request=trx_request,
                )

        # bank = Bank.objects.get(id=bank_id)
        
        # bank.status = "Not Active"
        # bank.updated_date = timezone.now()
        # bank.save()
        return JsonResponse({
            "message": "Payment deactivation request recorded successfully",
            "trx_id": trx.id,
            "status": trx.payment_status,
            "updated_date": trx.updated_at.isoformat() if trx.updated_at else None,
        }, status=200)

    except Transaction.DoesNotExist:
        logger.exception(
            f"Payment disable request failed | trx not found | trx_id={ref} | updated by={request.user} | error={str(e)}"
        )
        return Response({"error": "Transaction not found."},status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"Payment disable request failed | trx={ref} | updated by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def approve_payments(request, id):
    logger = logging.getLogger("make_payment")
    
    trx = None
    try:
        change = TransactionChangeRequest.objects.get(id=id)
        prev_trx = change.trx
        new = change.new_value
        old_value = change.old_value
        edir = change.edir
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            logger.exception(
                f"payment request approval failed because it's already processed | edirname={change.edir.name} | rejected by={request.user} "
            )
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        if change.action == "DISABLE": 
            bank_id = old_value.get("bank")
            total_amount = old_value.get("total_amount")
            method = old_value.get("method")
            image = change.image
            old_fees_data = old_value.get("fees", "[]")
            if isinstance(old_fees_data, str):
                old_fee_ids = json.loads(old_fees_data)
            else:
                old_fee_ids = old_fees_data

            for fee_id in old_fee_ids:
                fee_assign = FeeAssignment.objects.get(fee_id=fee_id, user = change.user)
                fee_assign.updated_date = timezone.now()
                fee_assign.transaction = None
                fee_assign.save() 

            if prev_trx:
                prev_trx.payment_status = "Disabled"
                prev_trx.updated_at = timezone.now()
                prev_trx.save()

            bank = Bank.objects.filter(id=bank_id)
            if bank:
                bank.amount = bank.amount - prev_trx.amount if prev_trx else bank.amount
                bank.updated_at = timezone.now()
                bank.save()

            change.status = "Approved"
            change.approved_at = timezone.now()
            change.checker = checker
            # change.trx= trx
            change.save()
        else:
                
            fees_data = new.get("fees", "[]")
            bank_id = new.get("bank")
            total_amount = new.get("total_amount")
            method = new.get("method")
            image = change.image
            # user_id = new.get("userId")

            if isinstance(fees_data, str):
                fee_ids = json.loads(fees_data)
            else:
                fee_ids = fees_data

            # fee_ids = [f.get("id") for f in fees if f.get("id")]

            # validate bank
            # bank = Bank.objects.filter(id=bank_id).first()
            bank = None
            if bank_id and str(bank_id).isdigit():
                bank = Bank.objects.filter(id=int(bank_id)).first()
            # edir= Edir.objects.get(id=edir_id)
            # user = CustomUser.objects.get(id=user_id)

            # assignments = FeeAssignment.objects.filter(
            #     fee_id__in=fee_ids,
            #     user=user,
            #     transaction__isnull=True   # ✅ prevent double payment
            # )

            # if not assignments.exists():
            #     return Response({"error": "No unpaid fees found"}, status=400)
            if bank and method == "transfer":
                deposit = Deposit.objects.create(
                    transaction_type="PAYMENT",
                    # amount=total_amount,
                    payment_method=method,
                    # edir=edir,
                    bank=bank,
                    image=image,
                    user=checker,
                    # payment_status="PAID"
                    reason=change.comment if change.comment else "Payment Disabled",
                )
            if prev_trx and method == "cash":
                deposit = prev_trx.deposit
            # ✅ create ONE transaction
            trx = Transaction.objects.create(
                transaction_type="PAYMENT",
                amount=total_amount,
                payment_method=method,
                edir=edir,
                # bank=bank,
                # image=image,
                user=change.user,
                payment_status="PAID",
                deposit = deposit if deposit else None
            )

            # parse fees
            # fee_ids = json.loads(fees_data)
            # fee_ids = [f["id"] for f in fees_data] if isinstance(fees_data, str) else fees_data
            

            if change.action == "UPDATE":    
                old_fees_data = change.old_value.get("fees", "[]")
                if isinstance(old_fees_data, str):
                    old_fee_ids = json.loads(old_fees_data)
                else:
                    old_fee_ids = old_fees_data
                
                for fee_id in old_fee_ids:
                    fee_assign = FeeAssignment.objects.get(fee_id=fee_id, user = change.user)
                    fee_assign.updated_date = timezone.now()
                    fee_assign.transaction = None
                    fee_assign.save() 

                for fee_id in fee_ids:
                    fee_assign = FeeAssignment.objects.get(fee_id=fee_id, user = change.user)
                    fee_assign.updated_date = timezone.now()
                    fee_assign.transaction = trx
                    fee_assign.save() 
                if prev_trx:
                    prev_trx.payment_status = "Modified"
                    prev_trx.updated_at = timezone.now()
                    prev_trx.save()

                bank = Bank.objects.filter(id=bank_id)
                if bank:
                    bank.amount = bank.amount - prev_trx.amount + total_amount if prev_trx else bank.amount + total_amount
                    bank.updated_at = timezone.now()
                    bank.save()

                change.status = "Approved"
                change.approved_at = timezone.now()
                change.checker = checker
                change.trx= trx
                change.save()
            elif change.action == "CREATE":
                if isinstance(fees_data, str):
                    fee_ids = json.loads(fees_data)
                else:
                    fee_ids = fees_data

                for fee_id in fee_ids:
                    fee_assign = FeeAssignment.objects.get(fee_id=fee_id, user = change.user, transaction__isnull=True)
                    fee_assign.updated_date = timezone.now()
                    fee_assign.transaction = trx
                    fee_assign.save() 

                bank = Bank.objects.filter(id=bank_id)
                if bank:
                    bank.amount = bank.amount + total_amount
                    bank.updated_at = timezone.now()
                    bank.save()

                change.status = "Approved"
                change.approved_at = timezone.now()
                change.checker = checker
                change.trx= trx
                change.save()
                # assignments.update(transaction=trx)

            logger.info(
                f"Payment created | trx={trx.reference} | assignments={len(fee_ids)} | by={request.user}"
            )
        # TrxAuditLog.objects.create(
        #     transaction=trx,
        #     action="TRX_CREATED",
        #     performed_by=request.user,
        #     new_status="Pending",
        #     new_value=model_to_json(trx),
        #     )

        return Response(
            {
                "transaction_id": trx.id if trx else None,
                "reference": trx.reference if trx else None,
                # "paid_fees": assignments.count(),
            },
            status=201,
        )
    
    # except Exception:
    #     logger.error(
    #         f"Failed to parse fees | fees_data={fees_data} | request_from={request.user}"
    #     )
    #     return Response({"error": "Invalid fees"}, status=400)
    
    except Edir.DoesNotExist:
        return Response({'error': 'edir not found'}, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.exception(
            f"transaction creation failed | trx={request.data} | created by={request.user} | error={str(e)}"
        )
        return Response(
            {"error": "Internal server error"},
            status=500,
        )


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def reject_payment (request, id):
    logger = logging.getLogger("fee")
    try:
        change = TransactionChangeRequest.objects.get(id=id)
        reason = request.data.get('reason')
        checker = EdirUser.objects.filter(
            user=request.user,
            edir=change.edir,
            status="Active"
        ).only("id").first()
        if change.status != "PENDING":
            logger.exception(
                f"Payment change request rejection failed because it's already processed | expense={change.new_value} | rejected by={request.user} | error=Already processed"
            )
            return Response(
                {"error": "Already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        # expense = Fee.objects.get(id=expense_id)
        # previous_expense = model_to_json(expense)

        change.status = "Rejected"
        change.approved_at = timezone.now()
        change.checker = checker
        change.comment= reason
        change.save()
        logger.info(
            f"User rejected payment change request successfully | rejected_by={request.user.id, request.user.phone_number} | payment={change.new_value}"
        )

        return JsonResponse({
            "message": "Payment request rejected successfully",
            "expense": change.new_value,
            "status": "Rejected",
            "updated_date": change.approved_at,
        }, status=200)
    # except Fee.DoesNotExist:
    #     return JsonResponse({"error": "Fee is not found "}, status=404)
    except Exception as e:
        logger.exception(
            f"Payment rejection failed | payment_id={change.new_value if 'change' in locals() else 'Unknown'} | rejected by={request.user} | error={str(e)}"
        )
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def unpay_fees(request):
    # fees = request.data.get("fees", "[]")
    fees_data = request.data.get("fees", "[]")
    try:
        fees = json.loads(fees_data)
    except json.JSONDecodeError:
        fees = []
    # Extract IDs safely from the list
    fee_ids = [fee.get("id") for fee in fees if "id" in fee]
    # Generate one trx_ref for this payment batch
    # trx_ref = str(uuid.uuid4())[:12]  # short unique string
    updated_count = FeeAssignment.objects.filter(
        id__in=fee_ids,
        payment_status="Paid"
    ).update(
        payment_status="Not Paid",
        paid_date=None,
        method=None,
        Trx_ref= None,
        bank = None,
        image = None
          # request.data.get("trx_ref", None)
    )

    return Response({"updated_count": updated_count}, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def deactivate_fee(request, fee_id):
    # Allow only PUT and PATCH
    if request.method not in ["PUT", "PATCH"]:
        return JsonResponse(
            {"error": "Only PUT or PATCH method allowed"},
            status=405
        )
    try:
        fee = Fee.objects.get(id=fee_id)
    except Fee.DoesNotExist:
        return JsonResponse({"error": "Fee not found"}, status=404)

    fee.status = "Not Active"
    fee.updated_date = timezone.now()
    fee.save()

    return JsonResponse({
        "message": "Fee deactivated successfully",
        "fee_id": fee.id,
        "status": fee.status,
        "updated_date": fee.updated_date,
    }, status=200)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def remove_payment(request, trx_ref):
    # fees = request.data.get("fees", [])

    # Extract IDs safely from the list
    # fee_ids = [fee.get("id") for fee in fees if "id" in fee]
    # Generate one trx_ref for this payment batch
    # trx_ref = str(uuid.uuid4())[:12]  # short unique string
    updated_count = FeeAssignment.objects.filter(
        Trx_ref=trx_ref,
        payment_status="Paid"
    ).update(
        payment_status="Not Paid",
        paid_date=None,
        method=None,
        Trx_ref= None # request.data.get("trx_ref", None)
    )

    return Response({"updated_count": updated_count}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    user.set_password(serializer.validated_data['new_password'])
    user.save()

    # Optionally: invalidate existing tokens (forces re-login)
    # Token.objects.filter(user=user).delete()

    return Response({'detail': 'Password changed successfully'}, status=status.HTTP_200_OK)
