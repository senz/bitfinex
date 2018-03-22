from __future__ import absolute_import
import requests
import json
import base64
import hmac
import hashlib
import random
import copy
import urlparse

PROTOCOL = "https"
HOST = "api.bitfinex.com"

STATUS_OK = requests.codes.ok
STATUS_TOO_MANY = requests.codes.too_many
STATUS_BAD = requests.codes.bad
STATUS_UNAUTH = requests.codes.unauthorized

DEFAULT_CONFIG = {
    "timeout": 5.0,
    "host": HOST,
    "protocol": PROTOCOL,
    "auth": {},
    "verify": True,
}


class RequestError(Exception):
    def __init__(self, response):
        """
        :type response: requests.models.Response
        """

        super(RequestError, self).__init__()
        split = urlparse.urlparse(response.url)
        self.path = split.path
        self.status = response.status_code

    def __str__(self):
        return "Request error for {} with status({})".format(self.path, self.status)


class NotConfigured(Exception):
    def __init__(self, parameter_name):
        super(NotConfigured, self).__init__()
        self.parameter_name = parameter_name

    def __str__(self):
        return "Parameter {} is not configured".format(self.parameter_name)


class BadAuth(RequestError):
    def __init__(self, response):
        """
        :type response: requests.models.Response
        """
        super(BadAuth, self).__init__(response)

        message = "<could not parse body>"
        try:
            json = response.json()
            message = json["message"] if json["message"] else message
        except ValueError as e:
            message += e.message

        self.message = message

    def __str__(self):
        return "Request auth failed: {}".format(self.message)


class RateLimitReached(RequestError):
    def __str__(self):
        return "Rate limit reached for {}".format(self.path)


class BitfinexClient:
    def __init__(self, options=None):
        self._session = None
        self.options = copy.deepcopy(DEFAULT_CONFIG)

        if options:
            self.options.update(options)

        self._is_auth = bool(self.options['auth']) and (bool(self.options['key']) and bool(self.options['secret']))
        self._secret_key = self.options['auth']['secret'].encode('utf8') if self.is_auth else None

        self.url = "{}://{}".format(self.options["protocol"], self.options["host"])

    @property
    def key(self):
        return self.options['auth']['key'] if self.is_auth else None

    @property
    def secret_key(self):
        return self._secret_key

    @property
    def is_auth(self):
        return self._is_auth

    @property
    def _nonce(self):
        """
        Returns a nonce
        Used in authentication
        """
        return str(random.randint(0, 100000000))

    def req_ticker(self, symbol):
        """
        https://docs.bitfinex.com/v1/reference#rest-public-ticker
        :type symbol: str
        """
        path = "/v1/ticker/{}".format(symbol)
        return self._make_get_request(path)

    def req_orderbook(self, symbol, params):
        """
        https://docs.bitfinex.com/v1/reference#rest-public-orderbook
        :type params: dict
        :type symbol: str
        """
        path = "/v1/book/{}".format(symbol)
        return self._make_get_request(path, query=params)

    def req_new_order(self, order):
        payload = order.to_dict()
        return self._make_post_request("/v1/order/new", payload)

    def req_new_orders(self, orders):
        payload = {"orders": orders}
        return self._make_post_request("/v1/order/new/multi", payload)

    def req_cancel_order(self, order_id):
        payload = {"id": order_id}
        return self._make_post_request("/v1/order/cancel", payload)

    def req_cancel_orders(self, order_ids):
        payload = {"orders": order_ids}
        return self._make_post_request("/v1/order/cancel/multi", payload)

    def req_active_orders(self):
        payload = {}
        return self._make_post_request("/v1/orders", payload)

    def req_order_status(self, order_id):
        payload = {"id": order_id}
        return self._make_post_request("/v1/order/status", payload)

    def _make_get_request(self, path, query=None):
        session = self._get_session()
        response = session.get(self.url + path, params=query)

        BitfinexClient._handle_response_errors(response)
        return response.json()

    def _make_post_request(self, path, payload):
        final_payload = copy.deepcopy(payload)
        final_payload["request"] = path
        final_payload["nonce"] = self._nonce

        signed_payload = self._sign_payload(final_payload)

        session = self._get_session()
        response = session.post(self.url + path, headers=signed_payload)

        BitfinexClient._handle_response_errors(response)

        return response

    @staticmethod
    def _handle_response_errors(response):
        if not response.status_code == STATUS_OK:
            if response.status_code == STATUS_UNAUTH:
                raise BadAuth(response)
            elif response.status_code == STATUS_TOO_MANY:
                raise RateLimitReached(response)
            else:
                raise RequestError(response)

    def _get_session(self):
        if not self._session:
            self._session = requests.Session()
            self._session.verify = self.options["verify"]

            if self.is_auth:
                self._session.headers.update({
                    "X-BFX-APIKEY": self.key,
                })

        return self._session

    def _sign_payload(self, payload):
        if not self.is_auth:
            raise NotConfigured("auth")

        j = json.dumps(payload, cls=BitfinexEncoder).encode("utf8")
        data = base64.standard_b64encode(j)

        h = hmac.new(self.secret_key, data, hashlib.sha384)
        signature = h.hexdigest()
        return {
            "X-BFX-SIGNATURE": signature,
            "X-BFX-PAYLOAD": data
        }


class Order(object):
    def __init__(self, symbol, amount, price, side, type, **kwargs):
        self.exchange = 'bitfinex'
        self.symbol = symbol
        self.amount = amount
        self.price = price
        self.side = side
        self.type = type

        self._additional_params = kwargs

    def to_dict(self):
        res = {
            "symbol": self.symbol,
            "amount": self.amount,
            "price": self.price,
            "exchange": self.exchange,
            "side": self.side,
            "type": self.type,
        }

        for k, v in self._additional_params:
            res[k] = v

        return res


class OrderEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Order):
            return o.to_dict()

        return super(OrderEncoder, self).default(o)


class BitfinexEncoder(OrderEncoder):
    pass
