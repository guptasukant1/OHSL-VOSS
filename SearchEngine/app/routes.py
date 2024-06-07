# app/routes.py
from flask import Blueprint, request, jsonify
from .scraper import scrape_website

main = Blueprint('main', __name__)

@main.route('/search', methods=['POST'])
def search():
    query = request.json.get('query')
    extracted_data = scrape_website(query)
    return jsonify({'data': extracted_data})