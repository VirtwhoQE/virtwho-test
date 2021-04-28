import pytest
from virtwho.settings import config


@pytest.fixture(scope='class', name='pool_id')
def get_pool_id(sm_guest, virtwho):
    """
    Get the pool id for case using, which is a class fixture, so
    will only run onece in the class.
    """
    vdc_pool = str()
    vdc_pool_virtual = str()
    global vdc_pool
    global vdc_pool_virtual
    virtwho.stop()
    sm_guest.unattach()
    vdc_id = config.sku.vdc
    vdc_sku = sm_guest.available(vdc_id)
    vdc_pool = vdc_sku['pool_id']
    vdc_id_virtual = config.sku.vdc_virtual
    vdc_sku_virtual = sm_guest.available(vdc_id_virtual, virtual=True)
    vdc_pool_virtual = vdc_sku_virtual['pool_id']


class TestRhsm:

    def test_demo_1(self, sm_guest, pool_id):
        """
        Just a demo
        """
        sm_guest.unattach()
        sm_guest.attach(pool=vdc_pool_virtual)
        sku = sm_guest.consumed(pool=vdc_pool_virtual)
        assert sku['temporary'] is True

    def test_demo_2(self, sm_virtwho, pool_id):
        sm_virtwho.unattach()
        sm_virtwho.attach(pool=vdc_pool)
        sku = sm_virtwho.consumed(pool=vdc_pool)
        assert sku
