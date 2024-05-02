from rest_framework import generics, authentication, permissions, viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.settings import api_settings
from apps.user.serializers import (
    UserSerializer,
    AuthTokenSerializer,
    RegisterUserSerializer,
    UserPasswordUpdateSerializer,
    UserListSerializer,
    WebAuthTokenSerializer,
)
from apps.user.permissions import ReferrerLimitPermission
from apps.user.models import Z2HUser, Z2HCustomers, Z2HUserRoles, Role
from apps.utils.tasks import send_email
import random
import string

class CreateUserView(generics.CreateAPIView):
    """Create a new user in the system."""
    serializer_class = UserSerializer

class ManageUserView(generics.RetrieveAPIView):
    """Manage the authenticated user."""
    serializer_class = UserSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Retrive and return the authenticated user."""
        return self.request.user

class ListUsersView(generics.ListAPIView):
    """List all the users in the system."""
    serializer_class = UserListSerializer
    authentication_classes = []
    permission_classes = []

    def get_queryset(self):
        """Return all the users."""
        return Z2HCustomers.objects.all()

class UserLoginView(ObtainAuthToken):
    """Create a new auth token for user."""
    serializer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES

    def handle_web_login(self, request_data):
        data = {
            'status': 'success',
            'message': 'Login Successful',
            'token': None,
        }

        serializer = WebAuthTokenSerializer(data=request_data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        data['token'] = token.key

        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        request_data = request.data

        accessed_from = request_data.get('accessed_from', None)

        if accessed_from == 'web':
            return self.handle_web_login(request_data)

        data = {
            'status': 'success',
            'message': 'Login Successful',
        }

        mobile_number = request_data.get('mobile_number')

        user_email = str(mobile_number) + "@z2h.com"
        z2h_user = Z2HUser.objects.filter(email=user_email).first()

        if z2h_user and z2h_user.is_first_login:
            z2h_user.is_first_login = False

        z2h_customer_uids = []
        z2h_customer = Z2HCustomers.objects.filter(user=z2h_user)
        if z2h_customer:
            z2h_customer_uids = [customer.uid for customer in z2h_customer]
        
        serializer = self.get_serializer(data=request_data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        data['token'] = token.key
        data['is_first_login'] = user.is_first_login
        data["customer_uids"] = z2h_customer_uids

        z2h_user.save()
        return Response(data, status=status.HTTP_200_OK)
    
class GetUserInfoView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        data = {
            'status': 'success',
            'message': 'User Infomation!!!',
        }
        user = request.user
        user_info = self.get_user_info(user)
        data['user_info'] = user_info
        return Response(data, status=status.HTTP_200_OK)

    def get_user_info(self, user):
        user_role = Z2HUserRoles.objects.filter(user_uid=str(user.uid)).first()
        role = Role.objects.filter(uid=user_role.role_uid).first()

        user_info = {
            'uid': user.uid,
            'name': user.name,
            'email': user.email,
            'role': role.name,
        }

        return user_info
    
class UserLogoutView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = {
            'status': 'success',
            'message': 'Logout Successful',
        }
        request.user.auth_token.delete()
        return Response(data, status=status.HTTP_200_OK)
    
class UpdatePasswordView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        data = {
            'status': 'success',
            'message': 'Password Updated Successfully',
        }
        user = request.user
        password = request.data.get('password')

        serialier = UserPasswordUpdateSerializer(data=request.data)

        if serialier.is_valid():
            user.set_password(password)
            user.is_password_updated = True
            user.save()
            return Response(data, status=status.HTTP_200_OK)

        data['message'] = serialier.errors
        data['status'] = 'error'
        return Response(data, status=status.HTTP_200_OK)
    
class RegisterUserView(APIView):
    authentication_classes = []
    permission_classes = [ReferrerLimitPermission, ]

    def generate_password(self, length=8):
        letters = string.ascii_letters
        digits = string.digits
        special_chars = string.punctuation

        password = ''.join(random.choices(letters, k=length-2))
        password += random.choice(letters.upper())
        password += random.choice(digits)
        password += random.choice(special_chars)

        password_list = list(password)
        random.shuffle(password_list)
        password = ''.join(password_list)

        return password

    def get_create_new_user(self, request_data):
        mobile_number = request_data.get('mobile_number')
        name = request_data.get('name')

        email = str(mobile_number) + "@z2h.com"

        check_user_exists = Z2HUser.objects.filter(email=email).exists()
        if check_user_exists:
            return "user_exists"

        password = self.generate_password()

        data = {
            'email': email,
            'password': password,
            'name': name,
        }

        user_serializer = UserSerializer(data=data)

        if user_serializer.is_valid():
            user_serializer.save()
            data = user_serializer.data
            data['password'] = password
            return data
        
        return None
    
    def post(self, request, *args, **kwargs):
        request_data = request.data

        referred_by = Z2HCustomers.objects.filter(uid=request_data.get('referred_by')).first()

        if not referred_by:
            data = {
                "status": "Error",
                "message": "No Referrer Found!!!"
            }
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        
        referred_by_id = referred_by.id
        request_data['referred_by'] = referred_by_id

        serializer = RegisterUserSerializer(data=request_data)

        if serializer.is_valid():
            new_user_password = self.get_create_new_user(request_data)

            if not new_user_password:
                data = {
                    "status": "Error",
                    "message": "Something went wrong!!!"
                }
                return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
            
            if new_user_password == "user_exists":
                data = {
                    "status": "Error",
                    "message": "User Already Exists!!!"
                }
                return Response(data=data, status=status.HTTP_400_BAD_REQUEST)

            serializer.save()

            user_uid = Z2HUser.objects.get(email=new_user_password['email']).uid

            password = new_user_password['password']

            data = {
                "status": "Success",
                "message": "User Created Successfully!!!",
                "uid": user_uid,
            }

            subject = "Zero To Hero Login Credentials"
            body = f"The System Generated Password for Zero To Hero Login of User '{request_data['name']}' is {password}"
            
            send_email(to_email=request_data['email_address'], body=body, subject=subject)

            return Response(data=data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ValidateReferrerView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        referrer_uid = request.query_params.get('referrer_uid', None)

        if not referrer_uid:
            data = {
                "status": "Error",
                "message": "Referrer UID is required!!!"
            }
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        
        referred_by = Z2HCustomers.objects.filter(uid=referrer_uid).first()
        if not referred_by:
            data = {
                "status": "Error",
                "message": "No Referrer Found!!!"
            }
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        
        data = {
            "status": "Success",
            "message": "Referrer Found!!!"
        }

        referrer_name = referred_by.user.name
        data["referrer_name"] = referrer_name
        
        return Response(data=data, status=status.HTTP_200_OK)
