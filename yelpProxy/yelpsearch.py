import webapp2
import logging
import urllib
import urllib2
import oauth2
import json
from jsonpath_rw import jsonpath, parse

class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('Hello, World')

class SearchHandler(webapp2.RequestHandler):
    HOST = "api.yelp.com"
    SEARCH_PATH = "/v2/search"

    def handle_exception(self, exception, debug):
        # Log the error.
        logging.exception(exception)
        
        response = self.response
        # If the exception is a HTTPException, use its error code.
        # Otherwise use a generic 500 error code.
        if isinstance(exception, webapp2.HTTPException):
            response.set_status(exception.code)
            response.write(exception.detail) 
        else:
            response.set_status(500)
            response.write(exception.message)

    def get_required_header(self, name):
        headers = self.request.headers
        if name not in headers:
            self.abort(400, detail="The required header '%s' is not provided"%(name))

        return headers[name]
    
    def get_value(self, jsonObj, path):
        """ Return a value for the given path. For example, 
            get_value({'a':{'b':{'c': 1}}}, "a.b.c") returns 1
        """
        if not json:
            return None

        if not path:
            return None
       
        try:
            expr = parse(path)
            result = [found.value.encode('ascii', errors="ignore") for found in expr.find(jsonObj)]
            if not result:
                return None
            return result[0]
        except Exception as e:
            self.abort(400, "Error when retrieving value: %s"%(e.message))
            

    def get(self):
        headers = self.request.headers
        consumer_key = self.get_required_header('OAUTH-CONSUMER-KEY')
        consumer_secret = self.get_required_header('OAUTH-CONSUMER-SECRET')
        token = self.get_required_header('OAUTH-TOKEN')
        token_secret = self.get_required_header('OAUTH-TOKEN-SECRET')

        search_query = self.request.query_string
        field = self.request.get('field') or "businesses.[0].name"
        search_result = self.do_search(search_query, field, consumer_key, consumer_secret, token, token_secret)

        self.response.headers['Content-type'] = 'text/plain'
        self.response.write(search_result)
    
    def do_search(self, query, field, consumer_key, consumer_secret, token, token_secret):
        """Returns response for API request."""
        # Unsigned URL
        if not query:
            self.abort(400, "You must provide search query")

        url = 'http://%s%s?%s' % (SearchHandler.HOST, SearchHandler.SEARCH_PATH, query)

        # Sign the URL
        consumer = oauth2.Consumer(consumer_key, consumer_secret)
        oauth_request = oauth2.Request('GET', url, {})
        oauth_request.update({
            'oauth_nonce': oauth2.generate_nonce(),
            'oauth_timestamp': oauth2.generate_timestamp(),
            'oauth_token': token,
            'oauth_consumer_key': consumer_key
        })

        token = oauth2.Token(token, token_secret)
        oauth_request.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), consumer, token)
        signed_url = oauth_request.to_url()

        # Connect
        try:
            conn = urllib2.urlopen(signed_url, None)
            try:
                response = self.get_value(json.loads(conn.read()), field)
            finally:
                conn.close()
        except urllib2.HTTPError, error:
            response = json.loads(error.read())

        return response

application = webapp2.WSGIApplication([
    ('/', MainPage), 
    ('/v2/search', SearchHandler)
    ], debug=True)
