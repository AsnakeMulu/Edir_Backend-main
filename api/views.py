from django.shortcuts import render
from django.db.models import Count, Sum, F, OuterRef, Subquery
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes, authentication_classes, parser_classes
from .serializers import UserWithNumFamSerializer, FamilyWithUserSerializer, EdirSerializer, UserWithEdirsSerializer, EdirDetailSerializer, EdirSerializer, FeeSerializer, FeeAssignmentReadOnlySerializer, ChangePasswordSerializer, FeeAssignmentDetailSerializer, FeeWithAssignmentsSerializer, UserDetailSerializer, BankWithEdirSerializer, EdirDetailSerializer, UserWithNumFam2Serializer, EdirSerializer, EdirWithUserStatusSerializer, HelpSerializer, EventSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import EdirAuditLog, Family, Edir, Fee, FeeAssignment, Bank, EdirUser, Help, Event, Transaction, UserAuditLog, EdirUserAuditLog
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

User = get_user_model()

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])  
def members_list_create(request, edir_id=None):
    if request.method == 'GET':
        try:
            edir = Edir.objects.get(id=edir_id)
        except Edir.DoesNotExist:
            return Response({"error": "Edir not found"}, status=status.HTTP_404_NOT_FOUND)
        
        edir_users = EdirUser.objects.filter(
            edir=edir,
            status__in=["Active", "Pending"]
        ).select_related("user")

        serializer = UserWithNumFam2Serializer(edir_users, many=True, context={"edir_id": edir.id})
        return Response(serializer.data, status=status.HTTP_200_OK) 

    if request.method == 'POST':
        data = request.data.copy()
        data['edir'] = edir_id 
        serializer = UserWithNumFamSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # or your custom permission
def active_members_list(request, edir_id=None):
        try:
            edir = Edir.objects.get(id=edir_id)
        except Edir.DoesNotExist:
            return Response({"error": "Edir not found"}, status=status.HTTP_404_NOT_FOUND)

        edir_users = EdirUser.objects.filter(
            edir=edir,
            status="Active"
        ).select_related("user")

        serializer = UserWithNumFamSerializer(edir_users, many=True, context={"edir_id": edir.id})
        return Response(serializer.data, status=status.HTTP_200_OK) 


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def members_by_edir(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
    except Edir.DoesNotExist:
        return Response({"error": "Edir not found"}, status=status.HTTP_404_NOT_FOUND)
        
    members = edir.users.all()
    data = [{"id": m.id, "name": m.full_name} for m in members]
    return Response(data, status=status.HTTP_200_OK)

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
    edir= None
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    # try:
    #     membership = GroupMembership.objects.get(user=user, group__edir_id=edir_id)
    # except GroupMembership.DoesNotExist:
    #     membership = None
    membership = None
    membership_status = "Not a Member"
    if edir_id is not None:
        try:
            edir = Edir.objects.get(id=edir_id)
        except Edir.DoesNotExist:
            return Response({"detail": "Edir not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            # membership = GroupMembership.objects.get(user=user, group__edir_id=edir_id)
            membership = EdirUser.objects.get(user=user, edir=edir)
            if membership.is_committee:
                membership_status = "Committee Member"
            else:
                membership_status = "Edir Member"
        except EdirUser.DoesNotExist:
            membership_status = "Not a Member"
    if request.method == 'GET':
        serializer = UserWithNumFamSerializer(user)
        # membership = GroupMembership.objects.get(user=user, group__edir_id=edir_id)
        response_data = serializer.data
        response_data["is_committee"] = membership.is_committee if membership else False
        response_data["membership_status"] = membership_status
        return Response(response_data, status=status.HTTP_200_OK)

    elif request.method in ['PUT', 'PATCH']:
        serializer = UserWithNumFamSerializer(user, data=request.data, partial=True)
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

@api_view(['POST'])
@permission_classes([AllowAny])
def self_register(request):
    logger = logging.getLogger("user_registration")
    if request.method == 'POST':
        try:
            logger.info("Self registration request received")
            data = request.data  # Use request.data to get JSON payload

            full_name = data.get('full_name')
            phone_number = data.get('phone_number')
            # email = data.get('email')
            gender = data.get('gender')
            marital_status = data.get('marital_status')
            profession = data.get('profession')
            address = data.get('address')
            password = data.get('password')

            if not full_name or not phone_number:
                logger.warning(
                    f"Validation failed - Missing fields | phone: {phone_number}"
                )
                return Response({'error': 'full_name and phone_number are required'}, status=status.HTTP_400_BAD_REQUEST)

            user = User.objects.create(
                full_name=full_name,
                phone_number=phone_number,
                # email=email,
                gender=gender,
                marital_status=marital_status,
                profession=profession,
                address=address,
                password=make_password(password),
            )
            user.save()

            UserAuditLog.objects.create(
            user=user,
            action="Self Registered",
            performed_by=user,
            new_value=model_to_dict(user, exclude=["password","last_login", "user_permissions","updated_date"]),
            )
            logger.info(
                f"User registered successfully | user_id={user.id} | phone={user.phone_number}"
            )
            return Response({'message': 'Registration successful'})
        except Exception as e:
            logger.exception(
                f"Registration failed | phone={request.data.get('phone_number')}"
            )

            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@api_view(['POST'])
def admin_create_user(request, edir_id):
    
    logger = logging.getLogger("user_added_by_user")
    try:
        logger.info("User added by admin request received")
        data = request.data  # Use request.data to get JSON payload

        full_name = data.get('full_name')
        phone_number = data.get('phone_number')
        # email = data.get('email')
        gender = data.get('gender')
        marital_status = data.get('marital_status')
        profession = data.get('profession')
        address = data.get('address')
        is_committee = data.get('is_Committee', False)

        if not full_name or not phone_number:
            logger.warning(
                f"Validation failed - Missing fields | phone: {phone_number}"
            )
            return Response({'error': 'full_name and phone_number are required'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create(
            full_name=full_name,
            phone_number=phone_number,
            # email=email,
            gender=gender,
            marital_status=marital_status,
            profession=profession,
            address=address,
        )
        user.set_unusable_password()
        user.save()
        logger.info(
            f"User added by admin successfully | user_id={user.id} | phone={user.phone_number}"
        )
        
        UserAuditLog.objects.create(
            user=user,
            action="Created by Admin",
            performed_by=request.user,
            new_value=model_to_dict(user, exclude=["password","last_login", "user_permissions","updated_date"]),
            )
    
        edir = Edir.objects.get(id=edir_id)
        edir.users.add(user) 
        # EdirUser.objects.create(
        #     user=user,
        #     edir=edir,
        #     is_committee=bool(is_committee )
        # )
        edir_user = EdirUser.objects.get(user=user, edir=edir)
        edir_user.is_committee = bool(is_committee)
        edir_user.save()
        logger.info(
            f"User added to edir successfully | user_id={user.id} | edir_id={edir.id}"
        )
        EdirUserAuditLog.objects.create(
            edirUser=edir_user,
            action="Added by Admin",
            performed_by=request.user,
            new_value=model_to_dict(edir_user),
            )


        return Response({'message': 'User created by admin'}, status=status.HTTP_201_CREATED)

    except Edir.DoesNotExist:
        return Response({'error': 'Edir not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"Registration failed | phone={request.data.get('phone_number')}"
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
    except Edir.DoesNotExist:
        return Response({'error': 'Edir not found'}, status=status.HTTP_404_NOT_FOUND)
    try:
        edir_user = EdirUser.objects.get(edir=edir, user=request.user)
        # edir_user = EdirUser.objects.get(user=user, edir=edir)
        edir_user.status = "Pending"
        edir_user.save()
    except EdirUser.DoesNotExist:
        # return JsonResponse({"error": "User is not found in Edir Request"}, status=404)
        EdirUser.objects.create(
            user=request.user,
            edir=edir,
            status= "Pending"
        )
    return Response({'message': 'User created by admin'}, status=status.HTTP_201_CREATED)


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
    # phone_number = request.data.get('phone_number')

    try:
        user = User.objects.get(phone_number=phone_number)
    except User.DoesNotExist:
        return Response({'exists': False}, status=status.HTTP_200_OK)

    try:
        edir = Edir.objects.get(id=edir_id)
    except Edir.DoesNotExist:
        return Response({'error': 'Edir not found'}, status=status.HTTP_404_NOT_FOUND)

    is_member = edir.users.filter(id=user.id).exists()

    return Response({'exists': is_member}, status=status.HTTP_200_OK)


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
                "full_name": user.full_name,
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
            {"exists": False, "error": f"Phone {phone_number} does not exist"},
            status=404
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def check_user_phone(request, phone_number):
    if not phone_number:
        return Response({'detail': 'Phone number is required.'}, status=status.HTTP_400_BAD_REQUEST)

    exists = User.objects.filter(phone_number=phone_number).exists()
    return Response({
        "phone_number": phone_number,
        "exists": exists
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def check_user_phoneNumber(request, phone_number):
    if not phone_number:
        return Response({'detail': 'Phone number is required.'}, status=status.HTTP_400_BAD_REQUEST)

    exists = User.objects.filter(phone_number=phone_number).exists()
    if (exists):
        user = User.objects.get(phone_number=phone_number)
        serializer = UserWithNumFamSerializer(user)
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
def deactivate_member(request, user_id, edir_id):
    # Allow only PUT and PATCH
    if request.method not in ["PUT", "PATCH"]:
        return JsonResponse(
            {"error": "Only PUT or PATCH method allowed"},
            status=405
        )
    try:
        edir = Edir.objects.get(id = edir_id)
    except Edir.DoesNotExist:
        return JsonResponse({"error": "Edir not found"}, status=404)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    
    try:
        edir_user = EdirUser.objects.get(user=user, edir = edir)
    except EdirUser.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    edir_user.status = "Not Active"
    edir_user.updated_date = timezone.now()
    edir_user.save()

    return JsonResponse({
        "message": "User deactivated from the Edir successfully",
        "user_id": user.id,
        "edir_id": edir.id,
        "status": edir_user.status,
        "updated_date": edir_user.updated_date,
    }, status=200)

@api_view(['POST'])
def add_family(request, user_id):
    data = request.data  
    # user = User.objects.get(id=user_id)
    # partner = None
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    relationship = data.get('relationship')
    full_name = data.get('full_name')
    gender = data.get('gender')
    # date_of_birth = data.get('date_of_birth')
    profession = data.get('profession')

    if not full_name :
        return Response({'error': 'full_name is required'}, status=status.HTTP_400_BAD_REQUEST)

    family = Family.objects.create(
        user = user,
        # partner= partner_user,
        full_name=full_name,
        gender=gender,
        # date_of_birth=date_of_birth,
        profession=profession,
        relationship=relationship,
    )
    family.save()
    return Response({'message': 'parther added by admin'}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_family_list(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        family = Family.objects.filter(user=user, status="Active")
    except User.DoesNotExist:
        return Response({"detail": "Partner not added"}, status=status.HTTP_404_NOT_FOUND)
    except Family.DoesNotExist:
        return Response({"detail": "Family not added"}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = FamilyWithUserSerializer(family, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def family_detail(request, user_id):
    try:
        family = Family.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"detail": "Partner not found"}, status=status.HTTP_404_NOT_FOUND)
    except Family.DoesNotExist:
        return Response({"detail": "Partner not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = FamilyWithUserSerializer(family)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        serializer = FamilyWithUserSerializer(family, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
    except Family.DoesNotExist:
        return JsonResponse({"error": "Family not found"}, status=404)

    family.status = "Not Active"
    family.updated_date = timezone.now()
    family.save()

    return JsonResponse({
        "message": "Family deactivated successfully",
        "bank_id": family.id,
        "status": family.status,
        "updated_date": family.updated_date,
    }, status=200)


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
    print("Edir creation request received")
    logger = logging.getLogger("user_registration")
    try:
        #Create Edir
        serializer = EdirSerializer(data=request.data)
        if serializer.is_valid():
            edir = serializer.save(created_by=request.user)
            logger.info(
                f"Edir Created by User successfully | edir_id={edir.id} | name={edir.name}"
            )
            
            EdirAuditLog.objects.create(
                edir=edir,
                action="CREATED",
                performed_by=request.user,
                new_value=model_to_dict(edir, exclude=["updated_date"]),
                )
            
            # Add creator as committee member of the Edir
            edir_user = EdirUser.objects.create(
                user=request.user,
                edir=edir,
                maker=request.user,
                is_committee=True,
                status="Active"
            )
            logger.info(
                f"User added to edir successfully when creating the edir as committee | user_id={request.user.id} | edir_id={edir.id}"
            )
            EdirUserAuditLog.objects.create(
                edirUser=edir_user,
                action="Added when Create Edir",
                performed_by=request.user,
                new_value=model_to_dict(edir_user),
                )

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            print(serializer.errors)
            return Response({'error': 'Bad request error', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception(
            f"Edir Creation failed | name={edir.name}"
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
    data = request.data  
    try:
        edir = Edir.objects.get(id=edir_id)
    except Edir.DoesNotExist:
        return Response({'error': 'edir not found'}, status=status.HTTP_404_NOT_FOUND)

    bank_name = data.get('bank_name')
    account_name = data.get('account_name')
    account_number = data.get('account_number')

    bank = Bank.objects.create(
        edir = edir,
        account_name=account_name,
        bank_name=bank_name,
        account_number=account_number,
    )
    bank.save()
    return Response({'message': 'bank added by admin'}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def edir_bank_list(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
        bank = Bank.objects.filter(edir=edir, status="Active")
    except Edir.DoesNotExist:
        return Response({"detail": "Edir not added"}, status=status.HTTP_404_NOT_FOUND)
    except Bank.DoesNotExist:
        return Response({"detail": "Bank not added"}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = BankWithEdirSerializer(bank, many=True)
    return Response(serializer.data)


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

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def deactivate_bank(request, bank_id):
    # Allow only PUT and PATCH
    if request.method not in ["PUT", "PATCH"]:
        return JsonResponse(
            {"error": "Only PUT or PATCH method allowed"},
            status=405
        )
    try:
        bank = Bank.objects.get(id=bank_id)
    except Bank.DoesNotExist:
        return JsonResponse({"error": "Bank not found"}, status=404)

    bank.status = "Not Active"
    bank.updated_date = timezone.now()
    bank.save()

    return JsonResponse({
        "message": "Bank deactivated successfully",
        "bank_id": bank.id,
        "status": bank.status,
        "updated_date": bank.updated_date,
    }, status=200)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_bank(request, bank_id):
    try:
        bank = Bank.objects.get(id=bank_id)
        bank.delete()
        return Response({"message": "Bank deleted successfully"}, status=status.HTTP_200_OK)
    except Bank.DoesNotExist:
        return Response({"error": "Bank not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def add_event(request, edir_id):
    data = request.data  
    try:
        edir = Edir.objects.get(id=edir_id)
    except Edir.DoesNotExist:
        return Response({'error': 'edir not found'}, status=status.HTTP_404_NOT_FOUND)

    title = data.get('title')
    description = data.get('description')
    caption = data.get('caption')
    date = data.get('date')
    location = data.get('location')
    # caption = data.get('caption')
    image = request.FILES.get("image")

    event = Event.objects.create(
        edir = edir,
        title=title,
        description=description,
        caption=caption,
        date=date,
        location=location,
        image =image
    )
    event.save()
    return Response({'message': 'Event added by admin'}, status=status.HTTP_201_CREATED)


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
        print("FILES:", request.FILES)
        print("DATA:", request.data)
        print("id:", event_id)
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

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_payments(request, user_id, edir_id):
    try:
        payments = (
            FeeAssignment.objects.filter(
                user_id=user_id,
                fee__edir_id=edir_id,
                Trx_ref__isnull=False,
                payment_status="Paid",
            )
            .values("Trx_ref")  # 👈 group by trx_ref only
            .annotate(
                total_amount=Sum("fee__amount"),
                method=F("method"),   # pick method from one row
                paid_date=F("paid_date"),  # pick paid_date from one row
                transaction_type=F("fee__transaction_type"),
                user_id=F("user_id"),
                edir_id=F("fee__edir_id"),
                fee_count=Count("fee"),
            )
            .order_by("-paid_date")
        )

        limit = request.query_params.get("limit")
        if limit is not None:
            try:
                limit = int(limit)
                payments = payments[:limit]
            except ValueError:
                return Response({"error": "Invalid limit"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(payments, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

import calendar
import datetime
from datetime import date
from dateutil.relativedelta import relativedelta

# def get_months_between(start_date, end_date):
#     months = []
#     current = date(start_date.year, start_date.month, 1)
#     while current <= end_date:
#         months.append(f"{calendar.month_name[current.month]} {current.year}")
#         # increment month
#         if current.month == 12:
#             current = date(current.year + 1, 1, 1)
#         else:
#             current = date(current.year, current.month + 1, 1)
#     return months

# def split_unpaid_months(unpaid_months):
#     today = datetime.date.today()

#     previous = []
#     future = []

#     for m in unpaid_months:
#         # parse "January 2025" -> datetime.date
#         parsed_date = datetime.datetime.strptime(m, "%B %Y").date().replace(day=1)

#         if parsed_date <= today.replace(day=1):
#             previous.append(m)
#         else:
#             future.append(m)

#     return previous, future

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def unpaid_months(request, edir_id):
#     user = request.user
#     today = date.today()
#     after_3_months = today + relativedelta(months=3)
#     try:
#         edir = Edir.objects.get(id=edir_id, users=user)
#     except Edir.DoesNotExist:
#         return Response({"error": "Edir not found or not joined"}, status=404)

#     # all possible months from started_date → today
#     start_date = date(2024, 6, 1)
#     all_months = get_months_between(start_date, after_3_months)

#     # paid months by this user in this edir
#     paid_months = list(
#         Bill.objects.filter(user=user, edir=edir)
#         .values_list("month", flat=True)
#     )

#     # unpaid = difference
#     unpaid = [m for m in all_months if m not in paid_months]
#     previous_months, future_months = split_unpaid_months(unpaid)
#     return Response({
#         "edir": edir.name,
#         "edir_fee":edir.monthly_fee,
#         "total_months": len(all_months),
#         "paid_months": paid_months,
#         "unpaid_months": previous_months,
#         "unpaid_future_months": future_months,
#         "unpaid_count": len(unpaid),
#     })

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_payment_details(request, payment_id):
#     try:
#         payment = Payment.objects.get(id=payment_id)
#     except Payment.DoesNotExist:
#         return Response({"error": "Payment not found"}, status=404)

#     serializer = PaymentDetailsSerializer(payment)
#     return Response(serializer.data)

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

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_fee_details(request, id):
    fee = get_object_or_404(Fee, id=id)

    # Get related FeeAssignments (user can be null)
    assignments = FeeAssignment.objects.filter(fee=fee).select_related("user")

    # Build assignment details safely
    assigned_users = []
    for a in assignments:
        if a.user:
            assigned_users.append({
                "user_id": a.user.id,
                "full_name": a.user.full_name.strip() if a.user.full_name else "Edir",
                "payment_status": a.payment_status,
                "paid_date": a.paid_date,
                "method": a.method,
                "trx_ref": a.Trx_ref,
            })
        else:
            # Handle null user (e.g., Edir or general fee)
            assigned_users.append({
                "user_id": None,
                "full_name": "Edir",
                "payment_status": a.payment_status,
                "paid_date": a.paid_date,
                "method": a.method,
                "trx_ref": a.Trx_ref,
            })

    # Fee details
    fee_data = {
        "id": fee.id,
        "name": fee.name,
        "reason": fee.reason,
        "amount": fee.amount,
        "category": fee.category,
        "payment_date": fee.payment_date,
        "edir_id": fee.edir_id,
        "assigned_users": assigned_users,
    }

    return Response(fee_data, status=200)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_payments(request, trx_ref):
    # Get all paid fees under this trx_ref
    fees = (
        FeeAssignment.objects.filter(Trx_ref=trx_ref, payment_status="Paid")
        .select_related("fee", "bank")  # optimize query
    )

    if not fees.exists():
        return Response({"detail": "No payments found."}, status=404)

    # Aggregate total once
    transaction_summary = fees.aggregate(total_amount=Sum("fee__amount"))
    first_fee = fees.first()
    # Build response
    data = {
        "trx_ref": trx_ref,
        "paid_date": first_fee.paid_date,
        "method": first_fee.method,
        "bank_name": first_fee.bank.bank_name if first_fee.bank else None,  # ✅ include bank name
        "image": request.build_absolute_uri(first_fee.image.url) if first_fee.image else None,
        "total_amount": transaction_summary["total_amount"],
        "fees": [
            {
                "id": f.id,
                "name": f.fee.name,
                "amount": f.fee.amount,
                "category": f.fee.category,
            }
            for f in fees
        ],
    }

    return Response(data)


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

@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def edir_detail(request, edir_id):
    user = request.user
    today = date.today()
    try:
        edir = Edir.objects.get(id=edir_id)
        if request.method == 'GET':
            serializer = EdirDetailSerializer(edir, context={"request": request})
            
        # data = serializer.data
        # data["member_count"] = edir.users.count()
        # data["unpaid_months"] = unpaid.count() 
            return Response(serializer.data)

        
        elif request.method in ['PUT', 'PATCH']:
            serializer = EdirSerializer(edir, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Edir.DoesNotExist:
        return Response({"error": "Edir not found."},status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def edir_details(request, edir_id):
    user = request.user
    today = date.today()
    try:
        edir = Edir.objects.get(id=edir_id)
        serializer = EdirDetailSerializer(edir, context={"request": request})

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

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_edir_withdrawals(request, edir_id):
    try:
        fees = Fee.objects.filter(edir_id=edir_id, transaction_type="Withdrawal").order_by("-id")

        # if not fees.exists():
        #     return Response({"error": "No withdrawals found for this edir"}, status=404)

        limit = request.query_params.get("limit")
        if limit is not None:
            try:
                limit = int(limit)
                fees = fees[:limit]
            except ValueError:
                return Response({"error": "Invalid limit"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = FeeWithAssignmentsSerializer(fees, many=True)
        return Response(serializer.data, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=400)

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

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_deposit_details(request, edir_id):
    payment_method = request.query_params.get("method")
    payment_date_str = request.query_params.get("payment_date")

    date_obj = parse_date(payment_date_str) if payment_date_str else None

    try:
        fees = FeeAssignment.objects.filter(
            fee__edir_id=edir_id,
            method=payment_method,
            payment_status="Paid",
            fee__transaction_type="Deposit",
            **({"paid_date__date": date_obj} if date_obj else {})
        ).select_related("fee", "user")

        if not fees.exists():
            return Response({"error": "No deposits found for this edir"}, status=404)

        # Group by user full name
        grouped = defaultdict(lambda: {
            "full_name": None,
            "method": None,
            "total_amount": Decimal("0.00"),
            "fees": []
        })

        for fee in fees:
            user_name = fee.user.full_name if fee.user else "Unknown"
            grouped[user_name]["full_name"] = user_name
            grouped[user_name]["method"] = payment_method
            grouped[user_name]["total_amount"] += fee.fee.amount
            grouped[user_name]["fees"].append({
                "fee_name": fee.fee.name,
                "fee_category": fee.fee.category,
                "amount": str(fee.fee.amount),
            })

        # response = {
        #     "paid_date": str(date_obj) if date_obj else None,
        #     "data": list(grouped.values())
        # }

        result = list(grouped.values())

        # Convert Decimal to string
        for item in result:
            item["total_amount"] = str(item["total_amount"])

        return Response(result, status=200)

        # Convert Decimal to string
        # for item in response["data"]:
        #     item["total_amount"] = str(item["total_amount"])

        # return Response(response, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_deposit_summary(request, edir_id):
    deposits = (
        FeeAssignment.objects.filter(
            fee__transaction_type="Deposit",
            payment_status="Paid",
            fee__edir_id=edir_id
        )
        .annotate(paid_day=TruncDate("paid_date"))  # group by date only
        .values("paid_day", "method")
        .annotate(total_amount=Sum("fee__amount"))
        .order_by("-paid_day")
    )

    limit = request.query_params.get("limit")
    if limit is not None:
        try:
            limit = int(limit)
            deposits = deposits[:limit]
        except ValueError:
            return Response({"error": "Invalid limit"}, status=status.HTTP_400_BAD_REQUEST)
    return Response(deposits, status=200)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_expense_detail(request, fee_id):
    try:
        fee = Fee.objects.get(id=fee_id)
        assignment = FeeAssignment.objects.get(fee=fee)

        serializer = FeeAssignmentDetailSerializer(assignment)
        return Response(serializer.data, status=200)

    except FeeAssignment.DoesNotExist:
        return Response({"error": "Fee assignment not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


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
    data = request.data
    try:
        edir = Edir.objects.get(id=edir_id)
    except Edir.DoesNotExist:
        return Response(
                {"error": "Edir not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    fee = Fee.objects.create(
        edir=edir,
        category=data.get("category"),
        name=data.get("name"),
        reason=data.get("reason"),
        amount=data.get("amount"),
        payment_date=data.get("payment_date"),
    )

    assign_type = data.get("assign_type")
    supported_member_id = data.get("supportedMember")

    member = None
    if supported_member_id:
        try:
            member = User.objects.get(id=supported_member_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Supported member not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if assign_type == "All Members":
        # members = edir.users.all()
        members = User.objects.filter(
            ediruser__edir=edir,
            ediruser__status="Active"
        )
        for m in members:
            if member and m == member:
                FeeAssignment.objects.create(fee=fee, user=m, payment_status="For You")
            else:
                FeeAssignment.objects.create(fee=fee, user=m)

    elif assign_type == "Custom Users":
        user_ids = data.get("users", [])
        # if member and supported_member_id not in user_ids:
        #     FeeAssignment.objects.create(fee=fee, user=member, payment_status="For You")

        for uid in user_ids:
            try:
                user = User.objects.get(id=uid)
                # if member and uid == supported_member_id:
                #     FeeAssignment.objects.create(fee=fee, user=user, payment_status="For You")
                # else:
                FeeAssignment.objects.create(fee=fee, user=user)
            except User.DoesNotExist:
                continue  # skip invalid users

    return Response(FeeSerializer(fee).data, status=status.HTTP_201_CREATED)


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_fee(request, fee_id):
    try:
        fee = Fee.objects.get(id=fee_id)
    except Fee.DoesNotExist:
        return Response({"error": "Fee not found"}, status=status.HTTP_404_NOT_FOUND)
    
    FeeAssignment.objects.filter(fee=fee, payment_status="Not Paid").delete()
    FeeAssignment.objects.filter(fee=fee, payment_status="For You").delete()

    data = request.data

    # update fee fields
    fee.category = data.get("category", fee.category)
    fee.name = data.get("name", fee.name)
    fee.reason = data.get("reason", fee.reason)
    fee.amount = data.get("amount", fee.amount)
    fee.payment_date = data.get("payment_date", fee.payment_date)
    fee.save()

    supportedMember = data.get("supportedMember")
    user_ids = data.get("users", [])

    if supportedMember and supportedMember not in user_ids:
        try:
            user = User.objects.get(id=supportedMember)
            FeeAssignment.objects.create(fee=fee, user=user, payment_status="For You")
        except User.DoesNotExist:
            pass

    for uid in user_ids:
        try:
            user = User.objects.get(id=uid)
            existing_assignment = FeeAssignment.objects.filter(fee=fee, user=user).exists()

            if not existing_assignment:
                if str(uid) == str(supportedMember):
                    FeeAssignment.objects.create(fee=fee, user=user, payment_status="For You")
                else:
                    FeeAssignment.objects.create(fee=fee, user=user)
        except User.DoesNotExist:
            continue

    return Response(FeeSerializer(fee).data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def withdraw(request, edir_id):
   
    data = request.data
    edir = Edir.objects.get(id=edir_id)

    expenseFor = data.get("expenseFor") 
    transaction_type=data.get("transaction_type")
    method=data.get("method")
    memberId=data.get("user")
    trx_ref = str(uuid.uuid4())[:12]

    if expenseFor != "Edir":
        user = User.objects.get(id=memberId)
    else:
        user = None
    fee = Fee.objects.create(
        edir=edir,
        category=data.get("category"),
        name=data.get("name"),
        reason=data.get("reason"),
        amount=data.get("amount"),
        transaction_type = transaction_type, 
    )

    # if expenseFor == "Member":
    FeeAssignment.objects.create(
        fee=fee, 
        user=user, 
        payment_status = "Paid", 
        method = method,
        paid_date = timezone.now(),
        Trx_ref = trx_ref)
    # else:
    #     FeeAssignment.objects.create(
    #         fee=fee, 
    #         # user=user, 
    #         # transaction_type = transaction_type, 
    #         payment_status = "Paid", 
    #         # method = method,
    #         paid_date = timezone.now(),
    #         Trx_ref = trx_ref)
    return Response(FeeSerializer(fee).data, status=status.HTTP_201_CREATED)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_expense(request, fee_id):
    try:
        fee = Fee.objects.get(id=fee_id)
    except Fee.DoesNotExist:
        return Response({"error": "Fee not found"}, status=status.HTTP_404_NOT_FOUND)
    
    FeeAssignment.objects.filter(fee=fee).delete()
   
    data = request.data
    # edir = Edir.objects.get(id=fee.edir)

    fee.category = data.get("category", fee.category)
    fee.name = data.get("name", fee.name)
    fee.reason = data.get("reason", fee.reason)
    fee.amount = data.get("amount", fee.amount)
    fee.transaction_type = data.get("transaction_type", fee.transaction_type)
    fee.save()

    expenseFor = data.get("expenseFor") 
    # transaction_type=data.get("transaction_type")
    memberId=data.get("user")
    trx_ref = str(uuid.uuid4())[:12]

    if expenseFor != "Edir":
        user = User.objects.get(id=memberId)
        FeeAssignment.objects.create(
        fee=fee, 
        user=user, 
        payment_status = "Paid", 
        paid_date = timezone.now(),
        Trx_ref = trx_ref)

    return Response(FeeSerializer(fee).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def fees_by_edir(request, edir_id):
    try:
        edir = Edir.objects.get(id=edir_id)
    except Edir.DoesNotExist:
        return Response({"error": "Edir not found"}, status=status.HTTP_404_NOT_FOUND)

    fees = Fee.objects.filter(edir=edir, transaction_type = "Deposit", status= "Active").order_by("-id")  

    # check for limit query param
    limit = request.query_params.get("limit")
    if limit is not None:
        try:
            limit = int(limit)
            fees = fees[:limit]
        except ValueError:
            return Response({"error": "Invalid limit"}, status=status.HTTP_400_BAD_REQUEST)


    serializer = FeeSerializer(fees, many=True)  # 👈 use serializer
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_unpaid_fees(request, edir_id, user_id):
    try:
        # Filter unpaid fees
        unpaid_fees = FeeAssignment.objects.filter(
            fee__edir_id=edir_id,
            fee__status="Active",
            user_id=user_id,
            payment_status="Not Paid"
        ).order_by("-id")

        serializer = FeeAssignmentReadOnlySerializer(unpaid_fees, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_paid_fees(request, trx_ref):
    try:
        # Filter unpaid fees
        paid_fees = FeeAssignment.objects.filter(
            Trx_ref=trx_ref,
            payment_status="Paid"
        )

        serializer = FeeAssignmentReadOnlySerializer(paid_fees, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

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
def admin_pay_fees(request):
    trx_ref = request.data.get("trx_ref")
    paid_date = request.data.get("paid_date")
    # bank_id = request.data.get("bank")
    # image = request.FILES.get("image")
    method = request.data.get("method")

    # ✅ Handle both string and list inputs
    fees_data = request.data.get("fees", [])
    if isinstance(fees_data, str):
        try:
            fees = json.loads(fees_data)
        except json.JSONDecodeError:
            fees = []
    else:
        fees = fees_data  # already a list

    # ✅ Get bank safely
    # try:
    #     bank = Bank.objects.get(id=bank_id)
    # except Bank.DoesNotExist:
    #     return Response({"error": "Bank not found"}, status=status.HTTP_404_NOT_FOUND)

    # Extract IDs safely
    fee_ids = [fee.get("id") for fee in fees if isinstance(fee, dict) and "id" in fee]

    # ✅ Generate transaction reference
    if not trx_ref:
        trx_ref = str(uuid.uuid4())[:12]

    # ✅ Parse paid_date if provided
    if paid_date:
        paid_date = parse_datetime(paid_date)
    if not paid_date:
        paid_date = timezone.now()

    # ✅ Loop and save files correctly
    updated_count = 0
    for fee_id in fee_ids:
        try:
            fee_assignment = FeeAssignment.objects.get(id=fee_id, payment_status="Not Paid")
            fee_assignment.payment_status = "Paid"
            fee_assignment.paid_date = paid_date
            fee_assignment.method = method
            fee_assignment.Trx_ref = trx_ref
            # fee_assignment.bank = bank
            # if image:
            #     fee_assignment.image = image
            fee_assignment.save()
            updated_count += 1
        except FeeAssignment.DoesNotExist:
            continue

    return Response({"updated_count": updated_count}, status=status.HTTP_200_OK)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def pay_fees(request):
    fees_data = request.data.get("fees", "[]")
    trx_ref = request.data.get("trx_ref")
    paid_date = request.data.get("paid_date")
    bank_id = request.data.get("bank")
    image = request.FILES.get("image")  # ✅ Correct way to get uploaded file
    method = request.data.get("method")

    # Parse fees safely
    try:
        fees = json.loads(fees_data)
    except json.JSONDecodeError:
        fees = []

    # Check bank
    try:
        bank = Bank.objects.get(id=bank_id)
    except Bank.DoesNotExist:
        bank = None
        # return Response({"error": "Bank not found"}, status=status.HTTP_404_NOT_FOUND)

    # Extract fee IDs
    fee_ids = [fee.get("id") for fee in fees if "id" in fee]

    # Generate trx_ref if missing
    if not trx_ref:
        trx_ref = str(uuid.uuid4())[:12]

    # Parse or default paid_date
    if paid_date:
        paid_date = parse_datetime(paid_date)
    if not paid_date:
        paid_date = timezone.now()

    # ✅ Loop through each FeeAssignment to save the file properly
    updated_count = 0
    for fee_id in fee_ids:
        try:
            fee_assignment = FeeAssignment.objects.get(id=fee_id, payment_status="Not Paid")
            fee_assignment.payment_status = "Paid"
            fee_assignment.paid_date = paid_date
            fee_assignment.method = method
            fee_assignment.Trx_ref = trx_ref
            fee_assignment.bank = bank
            if image:
                fee_assignment.image = image  # ✅ This triggers file saving
            fee_assignment.save()
            updated_count += 1
        except FeeAssignment.DoesNotExist:
            continue

    return Response({"updated_count": updated_count}, status=status.HTTP_200_OK)

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
