from builtins import object
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
    VMData,
    VMRequest,
    VMResponse,
)


class SandeshHandler(object):
    def __init__(self, database, lock):
        self._database = database
        self._lock = lock
        self._converter = SandeshConverter()

    def bind_handlers(self):
        DPGRequest.handle_request = self.handle_dpg_request
        VMRequest.handle_request = self.handle_vm_request
        GreenletObjectReq.handle_request = (
            self.handle_greenlet_obj_list_request
        )

    def handle_dpg_request(self, request):
        with self._lock:
            dpg_models = self._filter_dpg_models(request)
        response = DPGResponse(self._converter.convert_dpgs(dpg_models))
        response.response(request.context())

    def _filter_dpg_models(self, request):
        dpg_models = None
        if request.name is not None:
            dpg_model = self._database.get_dpg_model(request.name)
            if dpg_model is None:
                dpg_models = []
            else:
                dpg_models = [dpg_model]
        if dpg_models is None:
            dpg_models = self._database.get_all_dpg_models()
        if request.key is not None:
            dpg_models = [
                dpg_model
                for dpg_model in dpg_models
                if dpg_model.key == request.key
            ]
        if request.uuid is not None:
            dpg_models = [
                dpg_model
                for dpg_model in dpg_models
                if dpg_model.uuid == request.uuid
            ]
        if request.dvs_name is not None:
            dpg_models = [
                dpg_model
                for dpg_model in dpg_models
                if dpg_model.dvs_name == request.dvs_name
            ]
        return dpg_models

    def handle_vm_request(self, request):
        with self._lock:
            vm_models = self._filter_vm_models(request)
        response = VMResponse(self._converter.convert_vms(vm_models))
        response.response(request.context())

    def _filter_vm_models(self, request):
        vm_models = None
        if request.name is not None:
            vm_model = self._database.get_vm_model(request.name)
            if vm_model is None:
                vm_models = []
            else:
                vm_models = [vm_model]
        if vm_models is None:
            vm_models = self._database.get_all_vm_models()
        if request.host_name is not None:
            vm_models = [
                vm_model
                for vm_model in vm_models
                if vm_model.host_name == request.host_name
            ]
        if request.dpg_name is not None:
            dpg_model = self._database.get_dpg_model(request.dpg_name)
            if dpg_model is None:
                vm_models = []
            vm_models = [
                vm_model
                for vm_model in vm_models
                if vm_model.has_interface_in_dpg(dpg_model)
            ]
        return vm_models

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


class SandeshConverter(object):
    @classmethod
    def convert_dpgs(cls, dpg_models):
        return [
            DPGData(
                uuid=dpg_model.uuid,
                key=dpg_model.key,
                name=dpg_model.name,
                vlan_id=dpg_model.vlan_id,
                dvs_name=dpg_model.dvs_name,
            )
            for dpg_model in dpg_models
        ]

    @classmethod
    def convert_vms(cls, vm_models):
        return [
            VMData(
                name=vm_model.name,
                host_name=vm_model.host_name,
                dpgs=cls.convert_dpgs(vm_model.dpg_models),
            )
            for vm_model in vm_models
        ]
