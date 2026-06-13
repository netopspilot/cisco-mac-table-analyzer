from netmiko import ConnectHandler
from collections import Counter

username = input('Enter Username: ')
password = input('Enter Password: ')
ip = input('Enter IP: ')

iosv_l2 = {
    'device_type': 'cisco_ios',
    'ip': ip,
    'username': username,
    'password': password,
}

try:
    net_connect = ConnectHandler(**iosv_l2)
    print('=' * 50)

    # مرحله ۱ — CDP neighbors
    cdp = net_connect.send_command(
        'show cdp neighbors detail',
        use_textfsm=True
    )

    manageable_ports = []
    router_ports = []

    for n in cdp:
        cap = n.get('capabilities', '')
        port = n.get('local_port', '')
        if 'Switch' in cap:
            manageable_ports.append(port)
        elif 'Router' in cap:
            router_ports.append(port)

    print("سوئیچ‌های Manageable:")
    for p in manageable_ports:
        print(f"  ✅ {p}")

    print("روترها:")
    for p in router_ports:
        print(f"  🔵 {p}")

    print('=' * 50)

    # مرحله ۲ — MAC table
    output = net_connect.send_command(
        'show mac address-table',
        use_textfsm=True
    )

    counter = Counter(
        item['destination_port'][0]
        for item in output
        if item.get('destination_port')
        and item['destination_port'][0] != 'CPU'
    )

    # مرحله ۳ — تشخیص unmanaged
    print("پورت‌های مشکوک به سوئیچ Unmanaged:")
    unmanaged_found = False

    for port, count in counter.items():
        if (count >= 2
                and port not in manageable_ports
                and port not in router_ports):
            print(f"  ⚠️  {port} ({count} MAC)")
            unmanaged_found = True

    if not unmanaged_found:
        print("  سوئیچ unmanaged یافت نشد")

    print('=' * 50)

    # مرحله ۴ — ARP + MAC
    print("MAC Address و پورت:")
    arp = net_connect.send_command(
        'show arp',
        use_textfsm=True
    )

    for o in arp:
        mac = o.get('hardware_address', '')
        if not mac:
            continue
        r = net_connect.send_command(
            f'show mac address-table address {mac}',
            use_textfsm=True
        )
        if isinstance(r, list) and len(r) > 1:
            port = r[0].get('destination_port', '')
            print(f"  MAC: {mac} → Port: {port}")
        else:
            print(f"  MAC: {mac} → خود سوئیچ")

    print('=' * 50)

    # مرحله ۵ — پورت‌های Down
    print("اینترفیس‌های Down:")
    brief = net_connect.send_command(
        'show ip interface brief',
        use_textfsm=True
    )

    down_found = False
    for o in brief:
        if o.get('status') == 'down':
            print(f"  🔴 {o['interface']}")
            down_found = True

    if not down_found:
        print("  همه اینترفیس‌ها Up هستند")

    net_connect.disconnect()
    print('=' * 50)
    print('Finished ✅')

except Exception as e:
    print(f"خطا: {e}")
