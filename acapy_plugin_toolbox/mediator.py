"""Define messages and handlers for mediator admin protocol."""

# pylint: disable=invalid-name
# pylint: disable=too-few-public-methods
from marshmallow import fields

from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.core.protocol_registry import ProtocolRegistry
from aries_cloudagent.messaging.base_handler import (
    BaseHandler, BaseResponder, RequestContext
)
from aries_cloudagent.protocols.routing.v1_0.manager import RoutingManager
from aries_cloudagent.protocols.routing.v1_0.models.route_record import (
    RouteRecord, RouteRecordSchema
)
from aries_cloudagent.protocols.coordinate_mediation.v1_0.models.mediation_record import (
    MediationRecord, MediationRecordSchema
)
from aries_cloudagent.protocols.problem_report.v1_0.message import ProblemReport

from .util import generate_model_schema, admin_only
PROTOCOL = 'https://github.com/hyperledger/aries-toolbox/tree/master/docs/admin-mediator/0.1'

ROUTES_LIST_GET = '{}/routes_list_get'.format(PROTOCOL)
ROUTES_LIST = '{}/routes_list'.format(PROTOCOL)

MEDIATION_REQUESTS_GET = '{}/mediation-requests-get'.format(PROTOCOL)
MEDIATION_REQUESTS = '{}/mediation-requests'.format(PROTOCOL)

MESSAGE_TYPES = {
    ROUTES_LIST_GET:
        'acapy_plugin_toolbox.mediator.RoutesListGet',
}


async def setup(
        context: InjectionContext,
        protocol_registry: ProblemReport = None
):
    """Setup the issuer plugin."""
    if not protocol_registry:
        protocol_registry = await context.inject(ProtocolRegistry)
    protocol_registry.register_message_types(
        MESSAGE_TYPES
    )

MediationRequestsGet, MediationRequestsGetSchema = generate_model_schema(
    name='MediationRequestsGet',
    handler='acapy_plugin_toolbox.mediator.MediationRequestsGetHandler',
    msg_type=MEDIATION_REQUESTS_GET,
    schema={
        'state': fields.Str(required=True),
        'connection_id': fields.Str(required=False)
    }
)

MediationRequests, MediationRequestsSchema = generate_model_schema(
    name='MediationRequests',
    handler='acapy_plugin_toolbox.util.PassHandler',
    msg_type=MEDIATION_REQUESTS,
    schema={
        'requests': fields.List(fields.Nested(MediationRecordSchema))
    }
)


class MediationRequestsGetHandler(BaseHandler):
    """Handler for received mediation requests get messages."""

    @admin_only
    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle mediation requests get message."""
        tag_filter = dict(
            filter(lambda item: item[1] is not None, {
                'state': context.message.state,
                'connection_id': context.message.connection_id
            })
        )
        records = MediationRecord.query(context, tag_filter=tag_filter)
        response = MediationRequests(requests=records)
        response.assign_thread_from(context.message)
        await responder.send_reply(response)


RoutesListGet, RoutesListGetSchema = generate_model_schema(
    name='RoutesListGet',
    handler='acapy_plugin_toolbox.mediator.RoutesListHandler',
    msg_type=ROUTES_LIST_GET,
    schema={
    }
)

RoutesList, RoutesListSchema = generate_model_schema(
    name='RoutesList',
    handler='acapy_plugin_toolbox.util.PassHandler',
    msg_type=ROUTES_LIST,
    schema={
        'results': fields.List(fields.Dict())
    }
)


# TODO: Convert this to use coordinate-mediation models
# TODO: Change this to keylists-get as outlined in
#       docs/admin-mediator/1.0/README
# TODO: Prefer using RouteRecord directly over using the RoutingManager (it's
#       effectively the same thing)
class RoutesListHandler(BaseHandler):
    """Handler for received get cred list request."""

    @admin_only
    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle received get route list request."""

        mgr = RoutingManager(context)
        routes = await mgr.get_routes()  # connectionid, recipient key

        # post_filter_positive = dict(
        #     filter(lambda item: item[1] is not None, {
        #         # 'state': V10PresentialExchange.STATE_CREDENTIAL_RECEIVED,
        #         'role': V10PresentationExchange.ROLE_VERIFIER,
        #         'connection_id': context.message.connection_id,
        #         'verified': context.message.verified,
        #     }.items())
        # )
        records = [{
            'id:': r.record_id,
            'recipient_key': r.recipient_key,
            'connection_id': r.connection_id,
            'created_at': r.created_at,
        } for r in routes]
        list = RoutesList(results=records)
        list.assign_thread_from(context.message)
        await responder.send_reply(list)
