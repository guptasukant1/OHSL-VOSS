
import falcon
import requests

class HuggingFaceResource:
    def _init_(self, api_token):
        self.api_token = api_token
        self.api_url = "https://api-inference.huggingface.co/models/{model_name}"

    def on_post(self, req, resp, model_name):
        # Read the input data from the request
        input_data = req.media

        # Prepare the headers and payload for the Hugging Face API request
        headers = {
            "Authorization": f"Bearer {self.api_token}"
        }
        response = requests.post(self.api_url.format(model_name=model_name), headers=headers, json=input_data)

        # Set the response for the Falcon API
        resp.media = response.json()
        resp.status = falcon.HTTP_200

# Replace 'your_api_token' with your actual Hugging Face API token
api_token = "your_api_token"
hf_resource = HuggingFaceResource(api_token)

app = falcon.App()
app.add_route('/huggingface/{model_name}', hf_resource)

if _name_ == '_main_':
    from wsgiref import simple_server
    httpd = simple_server.make_server('127.0.0.1', 8000, app)
    print('Serving on http://127.0.0.1:8000')
    httpd.serve_forever()