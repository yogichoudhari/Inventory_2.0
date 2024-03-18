from datetime import timedelta
import json
import logging
import http.client

from decouple import config
from django.core.cache import cache
from django.shortcuts import render, redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from user.models import User as User 
from product.models import Product
from payment.models import PaymentLog
from .models import Survey
from product.models import Product
from inventory_management_system.utils import STATUS_SUCCESS, STATUS_FAILED
from .services import (
    get_auth_dialog,
    exchange_code_for_token,
    response_template,
    get_collector_url,
    get_survey,
)
import requests
import pdb


#Logger creation 
logger = logging.getLogger("file_logger")



# All bussiness logis are written below


@api_view(["GET"])
def oauth_dialog(request):
    auth_dialog_uri = get_auth_dialog()
    return Response(response_template(STATUS_SUCCESS, url=auth_dialog_uri), status=status.HTTP_200_OK)

@api_view(['GET'])
def get_oauth_code(request):
    try:
        # Extract the OAuth code from the query parameters
        code = request.query_params.get("code")

        # Exchange the code for an access token (assuming you have this function)
        access_token = get_token(code)

        # Return the access token in the response
        return Response({"access_token": access_token}, status=status.HTTP_200_OK)

    except Exception as e:
        # Log the exception for debugging purposes
        print(f"An error occurred: {e}")

        # Return an error response
        return Response({"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_token(auth_code):
    try:
        # Getting access token using auth code 
        access_json = exchange_code_for_token(auth_code)
        
        # Check if access_json dict has the access_token key or not
        if "access_token" in access_json:
            # Store the access_token in cache for accessing it later for working with Survey Monkey API
            cache.set('access_token', access_json['access_token'], timeout=None)
            
            # Return access token to the caller
            return access_json["access_token"]
        else:
            # if no access token found in response 
            return None
    except:
        return Response(response_template(STATUS_FAILED, message='An error occured'),
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

	
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_feedback(request, product_id):
    try:        
		# Extract User associated with the request
        user = User.objects.get(user=request.user)
        
		# Retrieve the Product using ID
        product = Product.objects.get(id=product_id)
        
		# Check if the Product is in user purchase history or not
        product_log = PaymentLog.objects.filter(product=product, user=user).last()
        
		# If yes then get the collector Url for getting feedback from the user
        collector_url = get_collector_url(product)

        if not product_log:
            # if Product is not available in User's purchase history
            return Response(response_template(STATUS_FAILED, error="product needs to be purchased first in order to review it"),
                            status=status.HTTP_400_BAD_REQUEST)

		# Return the collector URL in response for giving survey
        return Response(response_template(STATUS_SUCCESS, url=collector_url),
                        status=status.HTTP_200_OK)

    except Exception as e:
        # Log the exception for debugging purposes
        logger.exception("An error occurred in submit_feedback view {e}")
        # You can also return an error response if needed
        return Response(response_template(STATUS_FAILED, error="An error occurred"),
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated,IsAdminUser])
def feedback_list(request, product_id):
    try:
        # Retrieve the Product using ID we got in request
        product = Product.objects.get(id=product_id)
        
		# Retrive the Survey_Obj related to the particular product
        # which has survey collector url as well of this particular product
        survey_obj = Survey.objects.get(product=product)
        
		# Retrive the Survey ID of the survey 
        survey_id = survey_obj.survey_id
        
        # Get survey responses from surveymonkey using survey id
        survey_response = get_survey(survey_id)

		#return the  JSON Survey Response
        return Response(response_template(STATUS_SUCCESS, data=survey_response),
                        status=status.HTTP_200_OK)
    
	# If Given Product ID is incorrect or product does not exist in Product Table
    except Product.DoesNotExist:
        return Response(response_template(STATUS_FAILED, error="Product does not exist"),
                        status=status.HTTP_404_NOT_FOUND)

	# If Survey is not available for this product
    except Survey.DoesNotExist:
        return Response(response_template(STATUS_FAILED, error="Survey does not exist for the product"),
                        status=status.HTTP_404_NOT_FOUND)


      
      
    