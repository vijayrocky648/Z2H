from django.shortcuts import render
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework import authentication, permissions, status
from rest_framework import filters
from rest_framework.decorators import action
from django.core.paginator import Paginator
from .models import (
    Z2HPlanDetails,
    Z2HProductCategories,
    Z2HProductSubCategories,
    Z2HProducts,
    Z2HProductImages,
    Z2HOrders,
    Z2HOrderItems,
    Z2HAdvertisements,
    Z2HWebPages,
    Z2HWebPageRoles,
    Z2HProductsReturned,
)
from apps.app.serializers import (
    Z2HPlanDetailsSerializer,
    Z2HProductCategoriesSerializer,
    Z2HProductSubCategoriesSerializer,
    Z2HProductSerializer,
    Z2HOrderSerializer,
    Z2HOrderItemSerializer,
    Z2HAdvertisementsSerializer,
    Z2HWebPageSerializer,
    Z2HWebPageRolesSerializer,
    Z2HCreateProductSubCategoriesSerializer,
    Z2HProductsReturedSerializer,
)
from apps.user.serializers import RoleSerializer
from apps.user.models import Z2HCustomers, RegisterUser, Role
from apps.app.permissions import CustomerExistsPermission
from apps.utils.models import Z2HSettings
from django.utils import timezone
from django.http import FileResponse
import csv
import io
import os

# Create your views here.

LOOKUP_REGEX = '[0-9a-f-]{36}'
PRIMARY_LEG_COUNT = int(os.environ.get('PRIMARY_LEG_COUNT'))
SECONDARY_LEG_COUNT = PRIMARY_LEG_COUNT * PRIMARY_LEG_COUNT
TERTIARY_LEG_COUNT = SECONDARY_LEG_COUNT * PRIMARY_LEG_COUNT
QUATERNARY_LEG_COUNT = TERTIARY_LEG_COUNT * PRIMARY_LEG_COUNT

class Z2HPlanDetailsViewSet(ModelViewSet):
    queryset = Z2HPlanDetails.objects.all()
    serializer_class = Z2HPlanDetailsSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]
    lookup_field = 'uid'
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['id']
    ordering = ['id']

class Z2HProductCategoriesViewSet(ModelViewSet):
    queryset = Z2HProductCategories.objects.all()
    serializer_class = Z2HProductCategoriesSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]

    def perform_create(self, serializer):
        product_category_code_settings = Z2HSettings.objects.filter(name='product_category_code', is_active=True).first()
        product_category_code = product_category_code_settings.value

        product_category_sequence_settings = Z2HSettings.objects.filter(name='product_category_sequence', is_active=True).first()
        product_category_sequence = int(product_category_sequence_settings.value)

        product_category_sequence_settings.value = str(product_category_sequence + 1)
        product_category_sequence_settings.save()

        category_code = product_category_code + str(product_category_sequence)

        return serializer.save(category_code=category_code)

class Z2HProductSubCategoriesViewSet(ModelViewSet):
    queryset = Z2HProductSubCategories.objects.all()
    serializer_class = Z2HProductSubCategoriesSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]
    lookup_field = 'uid'
    lookup_url_kwarg = 'uid'
    lookup_value_regex = LOOKUP_REGEX

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return Z2HProductSubCategoriesSerializer
        
        return Z2HCreateProductSubCategoriesSerializer

    def get_queryset(self):
        return Z2HProductSubCategories.objects.filter(category__uid=self.kwargs['product_category_uid'])

    def perform_create(self, serializer):
        product_sub_category_code_settings = Z2HSettings.objects.filter(name='product_sub_category_code', is_active=True).first()
        product_sub_category_code = product_sub_category_code_settings.value

        product_sub_category_sequence_settings = Z2HSettings.objects.filter(name='product_sub_category_sequence', is_active=True).first()
        product_sub_category_sequence = int(product_sub_category_sequence_settings.value)

        product_sub_category_sequence_settings.value = str(product_sub_category_sequence + 1)
        product_sub_category_sequence_settings.save()

        sub_category_code = product_sub_category_code + str(product_sub_category_sequence)

        return serializer.save(sub_category_code=sub_category_code)
    
class Z2HProductsViewSet(ModelViewSet):
    queryset = Z2HProducts.objects.all()
    serializer_class = Z2HProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]
    lookup_field = 'uid'
    lookup_url_kwarg = 'uid'
    lookup_value_regex = LOOKUP_REGEX

    def get_queryset(self):
        product_type = self.request.query_params.get('product_type', None)

        if product_type and product_type == "all":
            return Z2HProducts.objects.filter(sub_category__uid=self.kwargs['product_sub_category_uid'])

        return Z2HProducts.objects.filter(sub_category__uid=self.kwargs['product_sub_category_uid'], is_active=True)
    
    @action(detail=False, methods=['POST', ], url_path='add', url_name='add')
    def add_product(self, request, *args, **kwargs):
        product_name = request.data.get('productName', None)
        product_description = request.data.get('productDescription', None)
        hsn_code = request.data.get('hsnCode', None)
        product_image_urls = request.data.get('productImageUrls', None)

        product_sub_category_obj = Z2HProductSubCategories.objects.filter(uid=self.kwargs['product_sub_category_uid']).first()

        product_code_settings = Z2HSettings.objects.filter(name='product_code', is_active=True).first()
        product_code_value = product_code_settings.value

        product_code_sequence_settings = Z2HSettings.objects.filter(name='prod_code_sequence', is_active=True).first()
        product_code_sequence = int(product_code_sequence_settings.value)

        product_code_sequence_settings.value = str(product_code_sequence + 1)
        product_code_sequence_settings.save()

        product_code = product_code_value + str(product_code_sequence)

        product = Z2HProducts.objects.create(
            name=product_name,
            description=product_description,
            price=0.00,
            discount=0.00,
            offer_price=0.00,
            hsn_code=hsn_code,
            sub_category=product_sub_category_obj,
            product_code=product_code,
            is_active=False,
        )

        for product_image in product_image_urls:
            Z2HProductImages.objects.create(product_image_url=product_image, product=product)

        created_product = Z2HProductSerializer(
            Z2HProducts.objects.get(id=product.id)
        ).data

        return Response(created_product, status=status.HTTP_200_OK)
    
class Z2HProductsListView(ListAPIView):
    queryset = Z2HProducts.objects.all()
    serializer_class = Z2HProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]

    def get_queryset(self):
        product_type = self.request.query_params.get('product_type', None)

        if product_type == "inactive":
            return Z2HProducts.objects.filter(is_active=False)

        return Z2HProducts.objects.filter(is_active=True)
    
class Z2HProductsPlanMapView(APIView):

    def post(self, request, *args, **kwargs):
        product_uid = request.data.get('product_uids', None)
        plan_uid = request.data.get('plan_uid', None)

        plan_obj = Z2HPlanDetails.objects.filter(uid=plan_uid).first()

        Z2HProducts.objects.filter(uid__in=product_uid).update(plan=plan_obj, is_active=True)

        return Response({"status": "success", "message": "Plan map updated successfully"}, status=status.HTTP_200_OK)

class Z2HOrdersSearchView(ListAPIView):
    queryset = Z2HOrders.objects.all()
    serializer_class = Z2HOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]
    
    def get_queryset(self):
        return Z2HOrders.objects.filter(order_number__icontains=str(self.kwargs['order_number']))
    
    def get(self, request, *args, **kwargs):
        data = self.get_queryset()
        return Response(data, status=status.HTTP_200_OK)
    
class Z2HOrderItemCount(ListAPIView):
    queryset = Z2HOrders.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]
    
    def get(self, request, *args, **kwargs):
        data = {
            "order_count": round(self.queryset.count() / 10)
        }
        return Response(data, status=status.HTTP_200_OK)
    
    
class Z2HOrdersListView(ListAPIView):
    queryset = Z2HOrderItems.objects.all()
    serializer_class = Z2HOrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]
    lookup_field = 'uid'
    lookup_url_kwarg = 'uid'
    lookup_value_regex = LOOKUP_REGEX

    def get_queryset(self):
        return Z2HOrderItems.objects.filter(order__ordered_by=self.request.user, product__uid=self.kwargs['product_uid'])
    
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        order = queryset.first().order

        data = {
            "products": self.get_serializer(queryset, many=True).data,
            "order": Z2HOrderSerializer(order).data
        }

        return Response(data, status=status.HTTP_200_OK)

class Z2HOrdersViewSet(ModelViewSet):
    queryset = Z2HOrders.objects.all()
    serializer_class = Z2HOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]
    lookup_field = 'uid'
    
    def get_paginationData(self, queryset, page="1", rowsPerPage="10"):
        paginator = Paginator(queryset, rowsPerPage)
        page_obj = paginator.get_page(page)
        data = {
            "data": page_obj.object_list,
            "total_page_count":round(queryset.count()/10),
        }
        return data
    
    def list(self, request, *args, **kwargs): 
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        page = self.request.query_params.get('page', None)
        rowsPerPage = self.request.query_params.get('rowsPerPage', None)
        pagination_data = self.get_paginationData(queryset, page=page, rowsPerPage=rowsPerPage)
        pagination_data['data'] = self.get_serializer(pagination_data['data'], many=True).data
        return Response(pagination_data, status=status.HTTP_200_OK)
        
    def get_queryset(self):
        from_date = self.request.query_params.get('fromDate', None)
        to_date = self.request.query_params.get('toDate', None)
        order_status = self.request.query_params.get('orderStatus', None)

        if order_status:
            order_status = order_status.lower()

        if from_date and to_date:
            if order_status == 'all':
                return self.queryset.filter(order_date__range=[from_date, to_date]).order_by("order_number")
            else:
                return self.queryset.filter(order_date__range=[from_date, to_date], order_status=order_status)
        
        return self.queryset.order_by("order_number")[:10]
    
    def partial_update(self, request, *args, **kwargs):
        orders = Z2HOrders.objects.filter(uid=kwargs['uid']).first()

        data = {
            "status": "success",
            "message": "Order updated successfully"
        }

        if orders.order_status == 'yet_to_be_couriered':
            orders.courier_date = request.data['courier_date']
            orders.delivery_details = request.data['delivery_details']
            orders.order_status = request.data['order_status']
            orders.save()
            return Response(data, status=status.HTTP_200_OK)

        Z2HOrders.objects.filter(uid=kwargs['uid']).update(
            delivery_date=request.data['delivery_date'],
            delivery_details=request.data['delivery_details'],
            order_status=request.data['order_status'],
            courier_date=request.data['courier_date'],
        )
        return Response(data, status=status.HTTP_200_OK)
    
class Z2HAdVideosView(ListAPIView):
    queryset = Z2HAdvertisements.objects.all()
    serializer_class = Z2HAdvertisementsSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]

    def get_queryset(self):
        return Z2HAdvertisements.objects.filter(name='demo_video', is_active=True)
    
class PostPaymentView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, CustomerExistsPermission]

    def check_required_key_exists(self, request_data_keys):
        required_keys = ['payment_mode', 'payment_status', 'payment_reference', 'product']
        for key in required_keys:
            if key not in request_data_keys:
                return False
        
        return True
    
    def check_product_exists(self, product_uid):
        return Z2HProducts.objects.filter(uid=product_uid, is_active=True).exists()
    
    def create_order(self, request, request_data):
        payment_details = {
            "payment_date": str(timezone.now()),
            "payment_mode": request_data['payment_mode'],
            "payment_status": request_data['payment_status'],
            "payment_reference": request_data['payment_reference']
        }

        settings_order_number_text = Z2HSettings.objects.filter(name='order_number_text', is_active=True).first()
        order_number_text = settings_order_number_text.value

        settings_order_number_sequence = Z2HSettings.objects.filter(name="order_number_sequence", is_active=True).first()
        order_number_value = int(settings_order_number_sequence.value)

        settings_order_number_sequence.value = str(order_number_value + 1)
        settings_order_number_sequence.save()

        order_number = order_number_text + str(order_number_value)

        z2h_orders = Z2HOrders.objects.create(
            ordered_by=request.user,
            order_date=timezone.now(),
            order_cgst_amount=0.0,
            order_sgst_amount=0.0,
            order_total_amount=0.0,
            order_status='yet_to_be_couriered',
            order_type='customer',
            delivery_date=None,
            delivery_details=None,
            payment_details=payment_details,
            courier_date=None,
            order_number=order_number,
        )

        return z2h_orders
    
    def create_order_details(self, request, request_data, order):
        product = Z2HProducts.objects.filter(uid=request_data['product']).first()

        settings_order_item_number_text = Z2HSettings.objects.filter(name='order_item_number_text', is_active=True).first()
        order_item_number_text = settings_order_item_number_text.value

        settings_order_item_number_sequence = Z2HSettings.objects.filter(name='order_item_number_sequence', is_active=True).first()
        order_item_number_sequence = int(settings_order_item_number_sequence.value)

        settings_order_item_number_sequence.value = str(order_item_number_sequence + 1)
        settings_order_item_number_sequence.save()

        order_item_number = order_item_number_text + str(order_item_number_sequence)

        cgst_percentage = 2.50
        cgst_amount = 2.50
        sgst_percentage = 2.50
        sgst_amount = 2.50
        igst_percentage = 0.00
        igst_amount = 0.00
        gst_total_amount = cgst_amount + sgst_amount + igst_amount
        price = float(product.plan.registration_fee) - cgst_amount - sgst_amount
        total_amount = price + gst_total_amount

        z2h_order_items = Z2HOrderItems.objects.create(
            order=order,
            product=product,
            hsn_code=product.hsn_code,
            quantity=1,
            price=price,
            cgst_percentage=cgst_percentage,
            cgst_amount=cgst_amount,
            sgst_percentage=sgst_percentage,
            sgst_amount=sgst_amount,
            igst_percentage=igst_percentage,
            igst_amount=igst_amount,
            gst_total_amount=gst_total_amount,
            total_amount=total_amount,
            order_item_number=order_item_number,
        )

        return z2h_order_items
    
    def update_order_details(self, request, order):
        z2h_order_items = Z2HOrderItems.objects.filter(order=order)

        order_cgst_amount = 0.0
        order_sgst_amount = 0.0
        order_gst_total_amount = 0.0
        order_total_amount = 0.0
        total_product_amount = 0.0

        for item in z2h_order_items:
            order_cgst_amount += float(item.cgst_amount)
            order_sgst_amount += float(item.sgst_amount)
            order_gst_total_amount += float(item.gst_total_amount)
            order_total_amount += float(item.total_amount)
            total_product_amount += float(item.price)

        Z2HOrders.objects.filter(uid=order.uid).update(
            order_cgst_amount=order_cgst_amount,
            order_sgst_amount=order_sgst_amount,
            order_gst_total_amount=order_gst_total_amount,
            order_total_amount=order_total_amount,
            total_product_price=total_product_amount,
        )

        return True
    
    def update_customer_details(self, request, order):
        register_user = RegisterUser.objects.filter(user=request.user).first()
        active_plan = Z2HPlanDetails.objects.get(name='Silver')

        settings_customer_number_text = Z2HSettings.objects.filter(name='customer_number_text', is_active=True).first()
        customer_number_text = settings_customer_number_text.value

        settings_customer_number_sequence = Z2HSettings.objects.filter(name='customer_number_value', is_active=True).first()
        customer_number_sequence = int(settings_customer_number_sequence.value)

        settings_customer_number_sequence.value = str(customer_number_sequence + 1)
        settings_customer_number_sequence.save()

        customer_number = customer_number_text + str(customer_number_sequence)

        customer = Z2HCustomers.objects.create(
            user=request.user,
            referrer=register_user.referred_by,
            active_plan_uid=active_plan.uid,
            plan_start_date=timezone.now(),
            customer_number=customer_number,
        )

        Z2HOrders.objects.filter(uid=order.uid).update(
            customer=customer
        )

        return True
        
    def update_referrer_level(self, request):
        z2hcustomer = Z2HCustomers.objects.filter(
            user=request.user,
            is_level_one_completed=False,
            is_level_two_completed=False,
            is_level_three_completed=False,
            is_level_four_completed=False
        )

        referrer_level_one = None
        referrer_level_two = None
        referrer_level_three = None
        referrer_level_four = None
        referrer_final_level = None

        referrer_level_one = z2hcustomer.first().referrer
        is_referrer_first_admin = referrer_level_one.is_admin_user

        if is_referrer_first_admin:
            referrer_final_level = referrer_level_one
        
        z2hcustomer_referrer_first = Z2HCustomers.objects.filter(id=referrer_level_one.id).first()

        z2hcustomers_under_referrer_first = Z2HCustomers.objects.filter(
            referrer=z2hcustomer_referrer_first
        ).exclude(
            is_admin_user=True
        )

        if not z2hcustomer_referrer_first.is_level_one_completed:
            if z2hcustomers_under_referrer_first.count() == PRIMARY_LEG_COUNT:
                z2hcustomer_referrer_first.is_level_one_completed = True
                z2hcustomer_referrer_first.level_one_completed_date = timezone.now()
                z2hcustomer_referrer_first.save()
        
        if referrer_level_one == referrer_final_level:
            return True

        ################## SECOND #######################
        
        referrer_level_two = Z2HCustomers.objects.filter(id=referrer_level_one.id).first().referrer
        is_referrer_second_admin = referrer_level_two.is_admin_user

        if is_referrer_second_admin:
            referrer_final_level = referrer_level_two
        
        # For Second Above Leg
        z2hcustomer_referrer_second = Z2HCustomers.objects.filter(id=referrer_level_two.id).first()

        # Taking the referrers under second leg
        z2hcustomer_under_referrer_second = Z2HCustomers.objects.filter(
            referrer=z2hcustomer_referrer_second
        ).exclude(
            is_admin_user=True
        )

        # Getting the count of customers under these referrers to update is_level_two_completed of referrer
        secondary_leg_count = 0
        for customer in z2hcustomer_under_referrer_second:
            secondary_leg_count += Z2HCustomers.objects.filter(referrer=customer).exclude(is_admin_user=True).count()

        if secondary_leg_count == SECONDARY_LEG_COUNT:
            z2hcustomer_referrer_second.is_level_two_completed = True
            z2hcustomer_referrer_second.level_two_completed_date = timezone.now()
            z2hcustomer_referrer_second.save()

        if referrer_level_two == referrer_final_level:
            return True

        ################## THIRD #######################

        referrer_level_three = Z2HCustomers.objects.filter(id=referrer_level_two.id).first().referrer
        is_referrer_third_admin = referrer_level_three.is_admin_user

        if is_referrer_third_admin:
            referrer_final_level = referrer_level_three

        # For Third Above Leg
        z2hcustomer_referrer_third = Z2HCustomers.objects.filter(id=referrer_level_three.id).first()

        # Taking the referrers under third leg
        z2hcustomer_under_referrer_third = Z2HCustomers.objects.filter(
            referrer=z2hcustomer_referrer_third
        ).exclude(
            is_admin_user=True
        )

        # Getting the count of customers under these referrers to update is_level_three_completed of referrer
        third_leg_count = 0
        for third_level_customer in z2hcustomer_under_referrer_third:
            for customer in Z2HCustomers.objects.filter(referrer=third_level_customer).exclude(is_admin_user=True):
                third_leg_count += Z2HCustomers.objects.filter(referrer=customer).exclude(
                    is_admin_user=True
                ).count()

        if third_leg_count == TERTIARY_LEG_COUNT:
            z2hcustomer_referrer_third.is_level_three_completed = True
            z2hcustomer_referrer_third.level_three_completed_date = timezone.now()
            z2hcustomer_referrer_third.save()

        if referrer_level_three == referrer_final_level:
            return True
        
        ################## FOURTH #######################
        referrer_level_four = Z2HCustomers.objects.filter(id=referrer_level_three.id).first().referrer

        # For Fourth Above Leg
        z2hcustomer_referrer_fourth = Z2HCustomers.objects.filter(id=referrer_level_four.id).first()

        # Taking the referrers under fouth leg
        z2hcustomer_under_referrer_fourth = Z2HCustomers.objects.filter(
            referrer=z2hcustomer_referrer_fourth
        ).exclude(
            is_admin_user=True
        )

        # Getting the count of customers under these referrers to update is_level_four_completed of referrer
        fourth_leg_count = 0
        for fourth_level_customer in z2hcustomer_under_referrer_fourth:
            for third_level_customer in Z2HCustomers.objects.filter(referrer=fourth_level_customer).exclude(is_admin_user=True):
                for customer in Z2HCustomers.objects.filter(referrer=third_level_customer).exclude(is_admin_user=True):
                    fourth_leg_count += Z2HCustomers.objects.filter(referrer=customer).exclude(
                        is_admin_user=True
                    ).count()
        
        if fourth_leg_count == QUATERNARY_LEG_COUNT:
            z2hcustomer_referrer_fourth.is_level_four_completed = True
            z2hcustomer_referrer_fourth.level_four_completed_date = timezone.now()
            z2hcustomer_referrer_fourth.plan_end_date = timezone.now()
            z2hcustomer_referrer_fourth.save()

        
    def post(self, request, *args, **kwargs):
        data = {
            'status': 'success',
            'message': 'Data Saved Successfully!!!',
        }

        request_data = request.data
        request_data_keys = request_data.keys()
        request_data_keys = list(request_data_keys)

        required_keys_exists = self.check_required_key_exists(request_data_keys)

        if not required_keys_exists:
            data['status'] = 'error'
            data['message'] = 'Required Details Not Found!!!'
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        
        if request_data['payment_status'] != 'success':
            data['status'] = 'error'
            data['message'] = 'Payment Failed!!!'
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        
        product_exists = self.check_product_exists(request_data['product'])

        if not product_exists:
            data['status'] = 'error'
            data['message'] = 'Product Not Found!!!'
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)

        create_order = self.create_order(request, request_data)
        create_order.save()

        create_order_details = self.create_order_details(request, request_data, create_order)
        create_order_details.save()

        update_order_details = self.update_order_details(request, create_order)

        if update_order_details:
            self.update_customer_details(request, create_order)
            self.update_referrer_level(request)
        
        user_customer = Z2HCustomers.objects.filter(user=request.user, is_level_four_completed=False).first()
        data["customer_uid"] = str(user_customer.customer_number)

        return Response(data=data, status=status.HTTP_200_OK)
    
class Z2HWebPagesView(ListAPIView):
    queryset = Z2HWebPages.objects.all()
    serializer_class = Z2HWebPageSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]

    def get(self, request, *args, **kwargs):
        role = Role.objects.filter(login_mode='web')
        data = {
            "pages": self.get_serializer(self.get_queryset(), many=True).data,
            "roles": RoleSerializer(role, many=True).data
        }

        return Response(data, status=status.HTTP_200_OK)
    
class SaveWebUserSettingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]

    def update_web_page_user(self, request_data, system_role_uid, users_page_uid):
        web_page_role = None

        if request_data['users'] == True:
            user_web_page_exists = Z2HWebPageRoles.objects.filter(
                role_uid=system_role_uid,
                web_page_uid=users_page_uid
            ).first()
            if not user_web_page_exists:
                web_page_role = Z2HWebPageRoles.objects.create(
                    role_uid=system_role_uid,
                    web_page_uid=users_page_uid
                )
            if user_web_page_exists:
                user_web_page_exists.is_active = True
                user_web_page_exists.save()

        elif request_data['users'] == False:
            web_page_role = Z2HWebPageRoles.objects.filter(
                role_uid=system_role_uid,
                web_page_uid=users_page_uid
            ).first()
            if web_page_role:
                web_page_role.is_active = False

        if web_page_role:
            web_page_role.save()
    
    def update_web_page_products(self, request_data, system_role_uid, products_page_uid):
        web_page_role = None

        if request_data['products'] == True:
            products_web_page_exists = Z2HWebPageRoles.objects.filter(
                role_uid=system_role_uid,
                web_page_uid=products_page_uid
            ).first()
            if not products_web_page_exists:
                web_page_role = Z2HWebPageRoles.objects.create(
                    role_uid=system_role_uid,
                    web_page_uid=products_page_uid
                )
            if products_web_page_exists:
                products_web_page_exists.is_active = True
                products_web_page_exists.save()

        elif request_data['products'] == False:
            web_page_role = Z2HWebPageRoles.objects.filter(
                role_uid=system_role_uid,
                web_page_uid=products_page_uid
            ).first()
            if web_page_role:
                web_page_role.is_active = False

        if web_page_role:
            web_page_role.save()
    
    def update_web_page_orders(self, request_data, system_role_uid, orders_page_uid):
        web_page_role = None

        if request_data['orders'] == True:
            orders_web_page_exists = Z2HWebPageRoles.objects.filter(
                role_uid=system_role_uid,
                web_page_uid=orders_page_uid
            ).first()
            if not orders_web_page_exists:
                web_page_role = Z2HWebPageRoles.objects.create(
                    role_uid=system_role_uid,
                    web_page_uid=orders_page_uid
                )
            if orders_web_page_exists:
                orders_web_page_exists.is_active = True
                orders_web_page_exists.save()

        elif request_data['orders'] == False:
            web_page_role = Z2HWebPageRoles.objects.filter(
                role_uid=system_role_uid,
                web_page_uid=orders_page_uid
            ).first()
            if web_page_role:
                web_page_role.is_active = False

        if web_page_role:
            web_page_role.save()
    
    def update_web_page_customer(self, request_data, system_role_uid, customers_page_uid):
        web_page_role = None

        if request_data['customers'] == True:
            customers_web_page_exists = Z2HWebPageRoles.objects.filter(
                role_uid=system_role_uid,
                web_page_uid=customers_page_uid
            ).first()
            if not customers_web_page_exists:
                web_page_role = Z2HWebPageRoles.objects.create(
                    role_uid=system_role_uid,
                    web_page_uid=customers_page_uid
                )
            if customers_web_page_exists:
                customers_web_page_exists.is_active = True
                customers_web_page_exists.save()

        elif request_data['customers'] == False:
            web_page_role = Z2HWebPageRoles.objects.filter(
                role_uid=system_role_uid,
                web_page_uid=customers_page_uid
            ).first()
            if web_page_role:
                web_page_role.is_active = False

        if web_page_role:
            web_page_role.save()
    
    def update_web_page_reports(self, request_data, system_role_uid, reports_page_uid):
        web_page_role = None

        if request_data['reports'] == True:
            reports_web_page_exists = Z2HWebPageRoles.objects.filter(
                role_uid=system_role_uid,
                web_page_uid=reports_page_uid
            ).first()
            if not reports_web_page_exists:
                web_page_role = Z2HWebPageRoles.objects.create(
                    role_uid=system_role_uid,
                    web_page_uid=reports_page_uid
                )
            if reports_web_page_exists:
                reports_web_page_exists.is_active = True
                reports_web_page_exists.save()

        elif request_data['reports'] == False:
            web_page_role = Z2HWebPageRoles.objects.filter(
                role_uid=system_role_uid,
                web_page_uid=reports_page_uid
            ).first()
            if web_page_role:
                web_page_role.is_active = False

        if web_page_role:
            web_page_role.save()
    
    def update_web_page_settings(self, request_data, system_role_uid, settings_page_uid):
        web_page_role = None

        if request_data['settings'] == True:
            settings_web_page_exists = Z2HWebPageRoles.objects.filter(
                role_uid=system_role_uid,
                web_page_uid=settings_page_uid
            ).first()
            if not settings_web_page_exists:
                web_page_role = Z2HWebPageRoles.objects.create(
                    role_uid=system_role_uid,
                    web_page_uid=settings_page_uid
                )
            if settings_web_page_exists:
                settings_web_page_exists.is_active = True
                settings_web_page_exists.save()

        elif request_data['settings'] == False:
            web_page_role = Z2HWebPageRoles.objects.filter(
                role_uid=system_role_uid,
                web_page_uid=settings_page_uid
            ).first()
            if web_page_role:
                web_page_role.is_active = False

        if web_page_role:
            web_page_role.save()

    def post(self, request, *args, **kwargs):
        data = {
            'status': 'success',
            'message': 'Data Saved Successfully!!!',
        }

        request_data = request.data

        system_role_uid = request_data['systemRoleUid']
        users_page = Z2HWebPages.objects.filter(name='users').first()
        products_page = Z2HWebPages.objects.filter(name='products').first()
        orders_page = Z2HWebPages.objects.filter(name='orders').first()
        customers_page = Z2HWebPages.objects.filter(name='customers').first()
        reports_page = Z2HWebPages.objects.filter(name='reports').first()
        settings_page = Z2HWebPages.objects.filter(name='settings').first()

        self.update_web_page_user(request_data, system_role_uid, users_page.uid)
        self.update_web_page_products(request_data, system_role_uid, products_page.uid)
        self.update_web_page_orders(request_data, system_role_uid, orders_page.uid)
        self.update_web_page_customer(request_data, system_role_uid, customers_page.uid)
        self.update_web_page_reports(request_data, system_role_uid, reports_page.uid)
        self.update_web_page_settings(request_data, system_role_uid, settings_page.uid)

        return Response(data=data, status=status.HTTP_200_OK)
    
class Z2HWebPageRolesView(ListAPIView):
    queryset = Z2HWebPageRoles.objects.all()
    serializer_class = Z2HWebPageRolesSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]

class Z2HProductsReturedViewset(ModelViewSet):
    queryset = Z2HProductsReturned.objects.all()
    serializer_class = Z2HProductsReturedSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]

def z2h_get_orders_template(request, from_date, to_date, order_status):
    orders = Z2HOrders.objects.filter(
        order_status=order_status
    )

    if from_date and to_date:
        orders = orders.filter(
            order_date__range=[from_date, to_date]
        )

    orders_data = Z2HOrderSerializer(orders, many=True).data

    file_headers = [
        'ORDER ID', 'ORDER DATE', 'CUSTOMER NAME', 'MOBILE NO.', 'ORDER TOTAL AMOUNT', 'DELIVERY ADDRESS', 'COURIER NAME', 'COURIER DATE [dd-mm-yyyy]', 
        'COURIER TRACKING NO.'
    ]

    csv_data = io.StringIO()
    csv_writer = csv.writer(csv_data)

    csv_writer.writerow(file_headers)

    for order in orders_data:
        delivery_address = order.get("delivery_address", None) or order.get("customer_address")

        data = [
            order["order_number"], 
            order["order_date"], 
            order["customer_name"], 
            order["mobile_number"], 
            order["order_total_amount"],
            delivery_address, 
            '', 
            '', 
            '',
        ]

        csv_writer.writerow(data)

    file_path = '/tmp/orders_download.csv'

    # Save the CSV data to a temporary file
    with open(file_path, 'w') as file:
        file.write(csv_data.getvalue())

    csv_file = open(file_path, 'rb')
    csv_data = csv_file.read().decode('utf-8')
    csv_file.close()

    os.remove(file_path)

    return FileResponse(csv_data, content_type='text/csv', filename='yet_to_be_couriered_orders.csv')

    