import click


class BridgeType(click.ParamType):
    name = '[mac:]bridge[:host_interface:guest_interface]'

    def convert(self, value, param, ctx):
        value = value.split(':')
        if len(value) == 1:
            return {'bridge': value[0]}
        if len(value) == 2:
            return {
                'mac': value[0],
                'bridge': value[1]
            }
        if len(value) == 3:
            return {
                'bridge': value[0],
                'host': value[1],
                'guest': value[2]
            }
        if len(value) == 4:
            return {
                'mac': value[0],
                'bridge': value[1],
                'host': value[2],
                'guest': value[3]
            }
        raise ValueError('Wrong bridge format: {}'.format(value))

BRIDGE = BridgeType()


@click.option("--bridge", "-b", multiple=True, type=BRIDGE)
def create(ctx, container, bridge, **kwargs):
    if len(bridge) > 0:
        container.manifest['networks'] = []
    for br in bridge:
        container.add_network(**br)


def update_sd_units(container, service, nspawn_args, capabilities):
    capabilities.append('CAP_NET_ADMIN')

    args = []
    for br in container.bridges:
        if 'guest_address' in br:
            args.append('--bridge {}:{}:{}:{}'.format(br['bridge'], br['host'], br['guest'], br['guest_address']))
        else:
            args.append('--bridge {}:{}:{}'.format(br['bridge'], br['host'], br['guest']))

        if 'ExecStopPost' not in service['Service']:
            service['Service']['ExecStopPost'] = []
        service['Service']['ExecStopPost'].append('/usr/bin/ip link del {}'.format(br['host']))

    service['Service']['ExecStart'] = '/usr/bin/env setup-netns ' + ' '.join(args) + ' ' + service['Service']['ExecStart']


def trim_interface_name(name):
    if len(name) >= 15:
        return name[0:15]
    return name


class NetworkContainer:
    @property
    def networks(self):
        return self.manifest.get('networks', [
            {"type": "bridge",
             "bridge": "br-lan",
             "host": trim_interface_name("vb-{}-lan".format(self.name)),
             "guest": "host0"
             },
        ])

    @property
    def bridges(self):
        return list(filter(lambda net: net['type'] == 'bridge', self.networks))

    def add_network(self, bridge, host=None, guest=None, mac=None):
        manifest = self.manifest
        if not host:
            host = "vb-{}-{}".format(self.name, bridge.split('-', 1)[1])
        if not guest:
            guest = "host-{}".format(bridge.split('-', 1)[1])

        if mac:
            mac = '{}:{}:{}:{}:{}:{}'.format(mac[0:2], mac[2:4], mac[4:6], mac[6:8], mac[8:10], mac[10:12])

        if any(filter(lambda net: net['host'] == host, self.networks)):
            raise ValueError('Duplicate host interface name: ' + host)

        if any(filter(lambda net: net['guest'] == guest, self.networks)):
            raise ValueError('Duplicate container interface name: ' + guest)

        if any(filter(lambda net: net.get('guest_address', '') == mac, self.networks)):
            raise ValueError('Duplicate guest mac address: ' + mac)

        if len(host) > 15:
            raise ValueError('Host interface name {} is {} bytes too long.'.format(host, len(host) - 15))

        if len(guest) > 15:
            raise ValueError('Container interface name {} is {} bytes too long.'.format(guest, len(guest) - 15))

        manifest['networks'].append({
            "type": "bridge",
            "bridge": bridge,
            "host": host,
            "guest": guest,
        })

        if mac:
            manifest['networks'][-1]['guest_address'] = mac

        self.manifest = manifest

    def default_manifest(self):
        super_dict = {}
        if hasattr(super(), 'default_manifest'):
            super_dict = super().default_manifest()

        super_dict.update({
            "networks": [
                {"type": "bridge",
                 "bridge": "br-lan",
                 "host": trim_interface_name("vb-{}-lan".format(self.name)),
                 "guest": "host0"},
            ],
        })

        return super_dict
