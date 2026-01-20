from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    CirculatingSupplyClient,
)


def test_pass_deploy(circulating_supply_client: CirculatingSupplyClient) -> None:
    configs = circulating_supply_client.state.box.get_all()
    assert not configs
