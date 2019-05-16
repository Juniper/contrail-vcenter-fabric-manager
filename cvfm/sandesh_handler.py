import gc
import traceback
import greenlet
from cfgm_common.uve.greenlets.ttypes import (
    GreenletObjectReq,
    GreenletObject,
    GreenletObjectListResp,
)
from cvfm.sandesh.vcenter_fabric_manager.ttypes import (
    DPGData,
    DPGRequest,
    DPGResponse,
)


class SandeshHandler(object):
    def __init__(self, database, lock):
        self._database = database
        self._lock = lock

    def bind_handlers(self):
        DPGRequest.handle_request = self.handle_dpg_request
        GreenletObjectReq.handle_request = (
            self.handle_greenlet_obj_list_request
        )

    def handle_dpg_request(self, request):
        dpgs = [
            DPGData(uuid="DPG1"),
            DPGData(uuid="DPG2"),
            DPGData(uuid="DPG3"),
        ]
        if request.uuid is not None:
            dpgs = [dpg for dpg in dpgs if dpg.uuid == request.uuid]
        response = DPGResponse(dpgs)
        response.response(request.context())

    @classmethod
    def handle_greenlet_obj_list_request(cls, request):
        greenlets = []
        for obj in gc.get_objects():
            if not isinstance(obj, greenlet.greenlet):
                continue
            greenlet_stack = "".join(traceback.format_stack(obj.gr_frame))
            greenlet_name = cls._get_greenlet_name(obj)
            greenlets.append(
                GreenletObject(
                    greenlet_traces=greenlet_stack, greenlet_name=greenlet_name
                )
            )
        if request.greenlet_name is not None:
            greenlets = [
                obj
                for obj in greenlets
                if obj.greenlet_name == request.greenlet_name
            ]
        response = GreenletObjectListResp(greenlets=greenlets)
        response.response(request.context())

    @classmethod
    def _get_greenlet_name(cls, obj):
        if not hasattr(obj, "greenlet_name"):
            try:
                greenlet_name = obj._run.__name__
            except AttributeError:
                greenlet_name = "Anonymous"
        else:
            greenlet_name = obj.greenlet_name
        return greenlet_name
