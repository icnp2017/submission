programs=$(patsubst %.p4, %.json, $(wildcard *.p4))

all : $(programs)

%.json : %.p4
	p4c-bmv2 --json $@ $< --primitives ../target/build/primitives.json

setup_network:
	@echo "Creating namespaces..."
	ip netns add ns1  
	ip netns add ns2
	@echo "Namespaces have been created."
	
	@echo "Creating links..."
	ip link add \
	    name ve1-0 address 00:04:00:00:00:01 \
	    type veth peer \
	    name ve1-1 address 00:aa:bb:00:00:01
	ip link set ve1-0 netns ns1
	
	ip link add \
	    name ve2-0 address 00:04:00:00:00:02 \
	    type veth peer \
	    name ve2-1 address 00:aa:bb:00:00:02
	ip link set ve2-0 netns ns2
	@echo "Links have been created."
	
	@echo "Diabling eth offload..."
	ethtool --offload ve1-1 rx off
	ethtool --offload ve1-1 tx off
	ethtool --offload ve1-1 sg off
	ethtool --offload ve2-1 rx off
	ethtool --offload ve2-1 tx off
	ethtool --offload ve2-1 sg off
	@echo "Eth offload has been disabled."
	
	@echo "Setting up IP addresses..."
	ip netns exec ns1 ip address add 10.1.1.10/24 dev ve1-0
	ip address add 10.1.1.1/24 dev ve1-1
	ip netns exec ns2 ip address add 10.1.2.10/24 dev ve2-0
	ip address add 10.1.2.1/24 dev ve2-1
	@echo "IP addresses have been set up"
	
	@echo "Bringing the devices up..."
	ip link set ve1-1 up
	ip link set ve2-1 up
	ip netns exec ns1 ip link set ve1-0 up
	ip netns exec ns2 ip link set ve2-0 up
	@echo "Devices have been brought up."
	
	@echo "Setting up routes..."
	ip netns exec ns1 ip route add default via 10.1.1.1 dev ve1-0 
	ip netns exec ns2 ip route add default via 10.1.2.1 dev ve2-0 
	@echo "Routes have been set up."

test_ping:
	ip netns exec ns1 ping 10.1.2.10 -c 4
	ip netns exec ns2 ping 10.1.1.10 -c 4

clean_network:
	@echo "Cleaning up..."
	ip netns del ns1
	ip netns del ns2
	@echo "Cleaned up!"

run_target:
	../target/build/simple_router -i 1@ve1-1 -i 2@ve2-1 -L info --log-console  ./simple_router.json

run_target_debug:
	../target/build/simple_router -i 1@ve1-1 -i 2@ve2-1 -L info --log-console --debugger ./simple_router.json

configure_target:
	PYTHONPATH=../p4t python -m p4t.cli < ./commands_opt.txt

	
.PHONY: setup_network clean_network
