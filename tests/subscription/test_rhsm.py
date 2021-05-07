
class TestRHSM:

    def test_demo(self, sm_guest, pool_id):
        """
        Just a demo
        """
        sm_guest.unattach()
        sm_guest.attach()
        sku = sm_guest.consumed(pool=pool_id)
        assert sku['temporary'] is True
