import ipaddress
import re

import pytest

from testkit import Exercise, TofuLab

ex = Exercise(__file__)
TIERS = ("public", "app", "db")
ANYWHERE = {"0.0.0.0/0", "::/0"}
ADDRESS = re.compile(r"^(aws_[a-z0-9_]+\.[A-Za-z0-9_-]+)")


@pytest.fixture(scope="module")
def planned_or_error():
    with TofuLab(ex.path("infra")) as tofu:
        try:
            tofu.init("-no-color")
            yield tofu.plan_json("-no-color")
        except pytest.fail.Exception as error:
            yield str(error)


@pytest.fixture
def plan(planned_or_error):
    if isinstance(planned_or_error, str):
        pytest.fail(planned_or_error)
    return planned_or_error


def planned(plan: dict) -> list[dict]:
    return plan.get("planned_values", {}).get("root_module", {}).get("resources", [])


def instances(plan: dict, type_: str, name: str | None = None) -> list[dict]:
    return [r for r in planned(plan) if r["type"] == type_ and (name is None or r["name"] == name)]


def config(plan: dict) -> dict[str, dict]:
    return {r["address"]: r for r in plan.get("configuration", {}).get("root_module", {}).get("resources", [])}


def refs(resource: dict, attribute: str) -> set[str]:
    expression = resource.get("expressions", {}).get(attribute) or {}
    found = list(expression.get("references", [])) if isinstance(expression, dict) else []
    if any(ref.startswith("each.value") for ref in found):
        found += resource.get("for_each_expression", {}).get("references", [])
    return {match.group(1) for ref in found if (match := ADDRESS.match(ref))}


def of_type(plan: dict, type_: str) -> list[dict]:
    return [r for r in config(plan).values() if r["type"] == type_]


def test_plan_only_creates(plan):
    actions = {r["address"]: r["change"]["actions"] for r in plan["resource_changes"] if r.get("mode") == "managed"}
    assert actions and all(a == ["create"] for a in actions.values()), actions


def test_three_tiers_in_two_azs(plan):
    vpc = instances(plan, "aws_vpc")
    assert len(vpc) == 1, f"Cần đúng một aws_vpc, đang có {len(vpc)}"
    network = ipaddress.ip_network(vpc[0]["values"]["cidr_block"])
    assert vpc[0]["values"].get("enable_dns_hostnames") is True, "Bật enable_dns_hostnames (RDS, VPC endpoint cần DNS)"
    seen = []
    for tier in TIERS:
        subnets = instances(plan, "aws_subnet", tier)
        zones = {s["values"]["availability_zone"] for s in subnets}
        assert len(subnets) >= 2 and len(zones) == len(subnets), f"aws_subnet.{tier}: cần mỗi AZ một subnet, ít nhất 2 AZ"
        for subnet in subnets:
            cidr = ipaddress.ip_network(subnet["values"]["cidr_block"])
            assert cidr.subnet_of(network), f"{subnet['address']} ({cidr}) nằm ngoài VPC {network}"
            clash = [address for address, other in seen if cidr.overlaps(other)]
            assert not clash, f"{subnet['address']} ({cidr}) trùng dải với {clash}"
            seen.append((subnet["address"], cidr))
            if tier != "public":
                assert subnet["values"].get("map_public_ip_on_launch") is False, \
                    f"{subnet['address']}: máy trong tầng {tier} không được tự nhận IP public"


def test_routes_per_tier(plan):
    resources = config(plan)
    inline = [a for a, r in resources.items() if r["type"] == "aws_route_table" and "route" in r.get("expressions", {})]
    assert not inline, f"Khai báo route bằng aws_route, không dùng khối route lồng trong {inline}"
    routes = of_type(plan, "aws_route")
    values = {r["address"]: r["values"] for r in instances(plan, "aws_route")}

    def default_routes(table: str) -> list[dict]:
        return [r for r in routes if f"aws_route_table.{table}" in refs(r, "route_table_id")
                and values.get(r["address"], {}).get("destination_cidr_block") == "0.0.0.0/0"]

    public = default_routes("public")
    assert len(public) == 1 and any(ref.startswith("aws_internet_gateway.") for ref in refs(public[0], "gateway_id")), \
        "Route table public cần đúng một route 0.0.0.0/0 tới Internet gateway"
    app = default_routes("app")
    assert len(app) == 1 and any(ref.startswith("aws_nat_gateway.") for ref in refs(app[0], "nat_gateway_id")), \
        "Route table app cần đúng một route 0.0.0.0/0 tới NAT gateway"
    assert not refs(app[0], "gateway_id"), "Route của tầng app không được đi thẳng ra Internet gateway"
    db = [r["address"] for r in routes if "aws_route_table.db" in refs(r, "route_table_id")]
    assert not db, f"Tầng db không cần route nào ra ngoài VPC: {db}"
    nats = of_type(plan, "aws_nat_gateway")
    assert nats and all(refs(n, "subnet_id") == {"aws_subnet.public"} for n in nats), "NAT gateway phải nằm trong subnet public"


def test_each_tier_uses_its_route_table(plan):
    associations = of_type(plan, "aws_route_table_association")
    for tier in TIERS:
        own = [a for a in associations if refs(a, "subnet_id") == {f"aws_subnet.{tier}"}]
        assert own, f"Chưa gắn aws_subnet.{tier} vào route table nào"
        for association in own:
            assert refs(association, "route_table_id") == {f"aws_route_table.{tier}"}, \
                f"{association['address']}: subnet {tier} phải dùng aws_route_table.{tier}"
        count = len([i for i in instances(plan, "aws_route_table_association") if any(i["address"].startswith(a["address"] + "[")
                                                                                     or i["address"] == a["address"] for a in own)])
        assert count == len(instances(plan, "aws_subnet", tier)), f"Mỗi subnet {tier} cần một association"


def rules(plan: dict, type_: str) -> list[dict]:
    values = {}
    for item in instances(plan, type_):
        values.setdefault(item["address"].split("[")[0], []).append(item["values"])
    found = []
    for resource in of_type(plan, type_):
        for value in values.get(resource["address"], []):
            found.append({"address": resource["address"], "group": refs(resource, "security_group_id"),
                          "source": refs(resource, "referenced_security_group_id"), "cidr": value.get("cidr_ipv4") or value.get("cidr_ipv6"),
                          "protocol": value.get("ip_protocol"), "from": value.get("from_port"), "to": value.get("to_port")})
    return found


def test_security_groups_chain(plan):
    inline = [a for a, r in config(plan).items() if r["type"] == "aws_security_group"
              and {"ingress", "egress"} & set(r.get("expressions", {}))]
    assert not inline, f"Khai báo rule bằng aws_vpc_security_group_*_rule, không dùng ingress/egress lồng trong {inline}"
    ingress = rules(plan, "aws_vpc_security_group_ingress_rule")
    problems = []
    for rule in ingress:
        if rule["cidr"] in ANYWHERE and rule["group"] != {"aws_security_group.alb"}:
            problems.append(f"{rule['address']}: chỉ load balancer được mở cho Internet")
        if rule["protocol"] in ("-1", "all") or rule["from"] != rule["to"]:
            problems.append(f"{rule['address']}: mở đúng một cổng TCP, không mở mọi giao thức hay một dải cổng")
    expected = [("aws_security_group.alb", None, 443), ("aws_security_group.app", "aws_security_group.alb", 8000),
                ("aws_security_group.db", "aws_security_group.app", 5432)]
    for group, source, port in expected:
        match = [r for r in ingress if r["group"] == {group} and r["protocol"] == "tcp" and r["from"] == r["to"] == port
                 and (r["cidr"] in ANYWHERE if source is None else r["source"] == {source})]
        if not match:
            problems.append(f"Thiếu rule vào {group} cổng {port} từ {source or 'Internet'}")
    for group in ("aws_security_group.app", "aws_security_group.db"):
        extra = [r["address"] for r in ingress if r["group"] == {group} and not (r["source"] and r["cidr"] is None)]
        if extra:
            problems.append(f"{group} chỉ nhận traffic từ security group tầng trước, không theo dải IP: {extra}")
    db = [r for r in ingress if r["group"] == {"aws_security_group.db"}]
    if any(r["source"] != {"aws_security_group.app"} or r["from"] != 5432 for r in db):
        problems.append("aws_security_group.db chỉ nhận 5432 từ aws_security_group.app")
    assert not problems, "\n".join(problems)


def test_database_private_encrypted_managed_password(plan):
    databases = instances(plan, "aws_db_instance")
    assert len(databases) == 1, f"Cần đúng một aws_db_instance, đang có {len(databases)}"
    values = databases[0]["values"]
    resource = config(plan)[databases[0]["address"].split("[")[0]]
    assert values.get("publicly_accessible") is False, "Database không được có IP public"
    assert values.get("storage_encrypted") is True, "Bật storage_encrypted"
    assert "password" not in resource.get("expressions", {}) and "password_wo" not in resource.get("expressions", {}), \
        "Không ghi mật khẩu trong cấu hình; để RDS tự quản trong Secrets Manager"
    assert values.get("manage_master_user_password") is True, "Dùng manage_master_user_password = true"
    assert refs(resource, "vpc_security_group_ids") == {"aws_security_group.db"}, "Database chỉ gắn aws_security_group.db"
    groups = refs(resource, "db_subnet_group_name")
    assert len(groups) == 1 and groups <= {r["address"] for r in of_type(plan, "aws_db_subnet_group")}, \
        "db_subnet_group_name phải tham chiếu một aws_db_subnet_group"
    assert refs(config(plan)[next(iter(groups))], "subnet_ids") == {"aws_subnet.db"}, "DB subnet group chỉ gồm subnet tầng db"
