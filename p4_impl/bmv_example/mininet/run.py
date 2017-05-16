import click

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.cli import CLI

from p4_mininet import P4Host, P4Switch


class TwoHostTopo(Topo):
    def __init__(self, sw_path, json_path):
        Topo.__init__(self)

        switch = self.addSwitch('s1', sw_path=sw_path, json_path=json_path)

        self.addLink(switch, self.addHost('h1', ip='10.1.1.10', mac='00:04:00:00:00:01'),
                     params1={'ip': '10.1.1.1', 'mac': '00:aa:bb:00:00:01'})
        self.addLink(switch, self.addHost('h2', ip='10.1.2.10', mac='00:04:00:00:00:02'),
                     params1={'ip': '10.1.2.1', 'mac': '00:aa:bb:00:00:02'})


@click.command()
@click.option('--target', required=True, help='Path to the target executable')
@click.option('--json', required=True, help='Path to the JSON program')
def main(target, json):
    topo = TwoHostTopo(target, json)
    net = Mininet(topo=topo, host=P4Host, switch=P4Switch, controller=None)
    CLI(net)
    net.stop()

if __name__ == '__main__':
    main()




