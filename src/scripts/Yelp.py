import pandas as pd
from flask import Flask, request, jsonify
from pyspark.mllib.recommendation import MatrixFactorizationModel
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("YelpRecommendationRestApi").getOrCreate()
app = Flask(__name__)


# TO handle CORS cross origin requests
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST')
    return response


app = Flask(__name__)


@app.route('/')
def index():
    return "Yelp Recommendation REST API is running. You can access the application using PostMan"


@app.route('/existingUserRecommendations/<int:userId>/<string:state>', methods=['GET'])
def get_existing_user_recommendation(userId, state):
    """
    Method to get restaurant recommendations for existing users
    :param userId: User Id
    :param state: State
    :return: 10 restaurant recommendations
    """
    user_detail = dict()
    user_detail['state'] = state
    user_detail['user_id'] = userId
    return get_recommendations_for_existing_user(user_detail)


def get_recommendations_for_existing_user(user_detail):
    """
    This method gets recommendations for existing users
    :param user_detail: user details
    :return: recommendations
    """
    user_state = user_detail['state']
    file_name = user_state + '_business.parquet'

    # load the als model based on the state
    model = load_als_model(file_name)

    user_id = user_detail['user_id']

    # using als model to get recommendations for existing user content based filtering
    recommendations = model.recommendProducts(user_id, 10)

    return get_recommendation_response(recommendations, user_detail)


def get_recommendation_response(recommendations, user_detail):
    """
    This methods forms a json output for the recommendation api
    :param recommendations: 10 recommendations of resturants
    :param user_detail: user state and id
    :return: 10 recommendations of resturants
    """
    result = dict()
    user_state = user_detail['state']

    reco_arr = []
    for reco in recommendations:
        print('reco :', reco)
        user = reco[0]
        product = reco[1]

        response = dict()
        response['business_id'] = product
        response['user_id'] = user

        # get business details based on the business id
        business_details = get_business_details(product, user_state)
        business_details = business_details.iloc[0]
        response['state'] = user_state
        response['business_id'] = business_details['business_id']
        response['business_name'] = business_details['name']
        response['business_address'] = business_details['address']
        response['business_stars'] = int(business_details['stars'])
        reco_arr.append(response)
    result['recommendations'] = reco_arr
    return jsonify(result)


def get_business_details(business_id, state):
    """
    Loads the state business details json file to get details
    :param business_id: id
    :param state: state
    :return: details
    """
    path = 'business/' + state + '_business_details.json'
    businessDf = pd.read_json(path, orient='records', lines=True)
    businessDetails = businessDf[businessDf['unique_business_id'] == business_id]
    return businessDetails


@app.route('/coldStartUserRecommendations', methods=['POST'])
def get_coldstart_user_recommendation():
    """
    Method to get restaurant recommendations for new users
    :return: recommendations for 10 restaurants
    """
    request_dict = request.json['coldstart']
    return get_cold_start_user_recommendation(request_dict)


def get_cold_start_user_recommendation(user_detail):
    """
    Method to get restaurant recommendations for new users
    :param user_detail: state and taste of the new user
    :return:
    """
    state = user_detail['state']
    tastes = user_detail['taste']

    file_name = state + '_business.parquet'

    # load model based on the state user is in
    model = load_als_model(file_name)
    suggestions = []
    final_recommendations = []

    # depending on the input provided by the user on various restaurants get users from he model
    for taste in tastes:
        suggested_users = model.recommendUsers(taste, 3)
        # get the resturants for the suggested users
        for u in suggested_users:
            suggested_products = model.recommendProducts(u[0], 3)
            for product in suggested_products:
                if product[1] not in suggestions:
                    suggestions.append(product[1])
                    final_recommendations.append(product)

    final_reco = sorted(final_recommendations, key=lambda x: x[2])
    return get_recommendation_response(final_reco, user_detail)


@app.route('/recommendProductForProducts', methods=['POST'])
def get_product_for_products_reco():
    request_dict = request.json['products']
    file_name = request_dict['state'] + '_business.parquet'
    model = load_als_model(file_name)
    users_suggested = model.recommendUsers(request_dict['business_id'], 3)
    suggestions = []
    final_recommendations = []
    for u in users_suggested:
        product_suggested = model.recommendProducts(u[0], 3)
        for p in product_suggested:
            if p[1] not in suggestions:
                suggestions.append(p[1])
                final_recommendations.append(p)

    final_reco = sorted(final_recommendations, key=lambda x: x[2])
    return get_recommendation_response(final_reco, request_dict)


def load_als_model(file_name):
    """
    loads ALS model based on state
    :param file_name: file
    :return: als model
    """
    return MatrixFactorizationModel.load(sc=spark.sparkContext,
                                         path='als-models/' + file_name)


if __name__ == '__main__':
    app.run(debug=True, port=8000)
