from .models import Survey
from django.core.cache import cache
from urllib.parse import urlencode
from decouple import config
import requests
from pdb import set_trace
SM_API_BASE = "https://api.surveymonkey.com"
AUTH_CODE_ENDPOINT = "/oauth/authorize"
ACCESS_TOKEN_ENDPOINT = "/oauth/token"
redirect_uri = "http://localhost:8000/api/surveys/oauth/callback"
CLIENT_ID = config("CLIENT_ID")
CLIENT_SECRET = config("CLIENT_SECRET")



def response_template(status,**response_obj):
    return {
        'status':status,
        'response':response_obj    
    }

def get_auth_dialog():
    import pdb
    pdb.set_trace()
    url_params = urlencode({
	    "redirect_uri": redirect_uri,
	    "client_id": CLIENT_ID,
	    "response_type": "code"
	})
    auth_dialog_uri = f"{SM_API_BASE}{AUTH_CODE_ENDPOINT}?{url_params}"
    return auth_dialog_uri

def exchange_code_for_token(auth_code):
    # set_trace()
    data = {
    	"client_secret": CLIENT_SECRET,
    	"code": auth_code,
    	"redirect_uri": redirect_uri,
    	"client_id": CLIENT_ID,
    	"grant_type": "authorization_code"
    }
    access_token_uri = SM_API_BASE + ACCESS_TOKEN_ENDPOINT
    access_token_response = requests.post(access_token_uri, data=data)
    access_json = access_token_response.json()
    return access_json
     

def create_survey_and_collector(product):
    try:
        url = "https://api.surveymonkey.com/v3/surveys"
        access_token = cache.get('access_token')
        headers = {
	    'accept': "application/json",
	    'Authorization': f"Bearer {access_token}",
		'Content-type':"application/json"
	    }
        survey_payload = {
          "title": " Product Quality Survey",
          "pages": [
            {
              "questions": [
              {
            "headings": [
                {
                    "heading": f"which star would you like to give {product.brand} {product.title}?"
                }
            ],
            "position": 1,
            "family": "matrix",
            "subtype": "rating",
            "display_options": {
                "display_type": "emoji",
                "display_subtype": "star"
            },
            "forced_ranking": False,
            "answers":{
            "rows": [
              {
                "visible": True,
                "text": "",
                "position": 1
              }
            ],
            "choices": [
              {
                "weight": 1,
                "text": ""
              },
              {
                "weight": 2,
                "text": ""
              },
              {
                "weight": 3,
                "text": ""
              },
              {
                "weight": 4,
                "text": ""
              },
              {
                "weight": 5,
                "text": ""
              }
            ]
          }
        }
              ]
            }
          ]
        }


        survey_res = requests.post(url,json=survey_payload,headers=headers)
        survey_id = survey_res.json().get("id")
        collector_creation_end_point = f"/{survey_id}/collectors"
        url = url+collector_creation_end_point
        collector_payload = {
  			"type": "weblink",
  			"name": "My Collector",
  			"thank_you_page": {
  			  "is_enabled": True,
  			  "message": "Thank you for taking this survey."
  			},
  			"thank_you_message": "Thank you for taking this survey.",
            "allow_multiple_responses": True,
		}
        collector_res = requests.post(url=url,json=collector_payload,headers=headers)
        collector_id = collector_res.json().get("id")
        Survey.objects.create(survey_id=survey_id,collector_id=collector_id,product=product)
        return True
    except Exception as e:
        return False
    

def get_collector_url(product):
    try:
        access_token = cache.get('access_token')
        headers = {
	    'accept': "application/json",
	    'Authorization': f"Bearer {access_token}"
	    }
        survey_obj = Survey.objects.get(product=product)
        collector_id = survey_obj.collector_id
        endpoint_url = f"/v3/collectors/{collector_id}"
        url = SM_API_BASE + endpoint_url
        collector = requests.get(url=url,headers=headers)
        collector_url = collector.json().get('url')
        return collector_url
    except:
        pass


def get_survey(survey_id):
    try:
        endpoint_url = f"/v3/surveys/{survey_id}/trends"
        url = SM_API_BASE + endpoint_url
        access_token = cache.get('access_token')
        headers = {
	    'accept': "application/json",
	    'Authorization': f"Bearer {access_token}"
	    }
        survey_res = requests.get(url=url,headers=headers)
        survey_data = survey_res.json()
        total_responses = survey_data["data"][0]["trends"][0]["rows"][0].get("total")
        survey_ans_list = survey_data["data"][0]["trends"][0]["rows"][0].get("choices")
        survey_ans_dict = {str(i):survey_ans_list[i-1]["count"] for i in range(1,len(survey_ans_list)+1)}
        response_dict = {}
        def average_res(d):
            total_response_count = 0
            counter = 1
            for _,v in d.items():
                total_response_count+=int(counter)*int(v)
                response_dict[f"{counter}_star"] = v
                counter+=1
            return total_response_count/total_responses
        response_dict["average_response"] = average_res(survey_ans_dict)
        response_dict["total_response"] = total_responses
        return response_dict
    except:
        pass