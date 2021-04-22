from virtwho.runner import VirtwhoRunner
from virtwho.configure import VirtwhoHypervisorConfig
from virtwho.configure import VirtwhoGlobalConfig
from virtwho.register import SubscriptionManager

esx = VirtwhoHypervisorConfig('esx', 'rhsm')
virtwhoconf = VirtwhoGlobalConfig('esx')
virtwho = VirtwhoRunner('esx', 'rhsm')
sm = SubscriptionManager('esx', 'rhsm')


class TestEsx:

    @classmethod
    def setup_class(cls):
        """Initiate at the beginning of the test class.
        Clean all configurations for /etc/virt-who.conf
        Clean hosts on register servers web.
        Stop virt-who service
        Register both the virt-who host and guest
        Get PoolID for each tested subscriptions.
        """
        virtwhoconf.clean()
        virtwho.virtwho_stop()
        # server_web_clean
        sm.register()
        sm.register(guest=True)

        cls.vdc = sm.sku_attributes(
            sku_name='vdc', virtual=False, guest=True).sku['pool_id']
        cls.vdc_virtual = sm.sku_attributes(
            sku_name='vdc_virtual', virtual=True, guest=True).sku['pool_id']
        cls.unlimit = sm.sku_attributes(
            sku_name='unlimit', virtual=False, guest=True).sku['pool_id']
        cls.unlimit_virtual = sm.sku_attributes(
            sku_name='unlimit', virtual=True, guest=True).sku['pool_id']
        cls.limit = sm.sku_attributes(
            sku_name='limit', virtual=False, guest=True).sku['pool_id']
        cls.limit_virtual = sm.sku_attributes(
            sku_name='limit', virtual=True, guest=True).sku['pool_id']
        cls.instance = sm.sku_attributes(
            sku_name='limit', virtual=False, guest=True).sku['pool_id']

    def test_vdc_sku(self):
        """
        Just a demo
        :return:
        """
        virtwho.run_cli()
        #rhsm.sku_attach(pool=self.vdc)
        sm.sku_attach(pool=self.vdc_virtual, guest=True)
        sku = sm.sku_consumed(pool=self.vdc_virtual, guest=True)
        assert (sku['sku_type'] is 'Virtual'
                and sku['temporary'] is False)
        #rhsm.sku_unattach(pool=self.vdc)
        sku = sm.sku_consumed(pool=self.vdc_virtual, guest=True)
        assert sku is None
