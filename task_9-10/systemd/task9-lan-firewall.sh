#!/bin/sh
set -eu
IPT=/usr/sbin/iptables

$IPT -N TASK9-LAN-INPUT 2>/dev/null || true
$IPT -F TASK9-LAN-INPUT
$IPT -A TASK9-LAN-INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
$IPT -A TASK9-LAN-INPUT -s 192.168.0.0/24 -p udp --sport 67 --dport 68 -j ACCEPT
$IPT -A TASK9-LAN-INPUT -j DROP
while $IPT -C INPUT -i enp0s9 -j TASK9-LAN-INPUT 2>/dev/null; do
  $IPT -D INPUT -i enp0s9 -j TASK9-LAN-INPUT
done
$IPT -I INPUT 1 -i enp0s9 -j TASK9-LAN-INPUT

$IPT -N TASK9-LAN-FORWARD 2>/dev/null || true
$IPT -F TASK9-LAN-FORWARD
$IPT -A TASK9-LAN-FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
$IPT -A TASK9-LAN-FORWARD -s 192.168.0.0/24 -d 10.42.0.0/16 -p tcp --dport 80 -m conntrack --ctstate NEW --ctorigdstport 80 -j ACCEPT
$IPT -A TASK9-LAN-FORWARD -s 192.168.0.0/24 -d 10.42.0.0/16 -p tcp --dport 443 -m conntrack --ctstate NEW --ctorigdstport 443 -j ACCEPT
$IPT -A TASK9-LAN-FORWARD -j DROP
while $IPT -C FORWARD -i enp0s9 -j TASK9-LAN-FORWARD 2>/dev/null; do
  $IPT -D FORWARD -i enp0s9 -j TASK9-LAN-FORWARD
done
$IPT -I FORWARD 1 -i enp0s9 -j TASK9-LAN-FORWARD
