from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    CirculatingSupplyClient,
)

from .conftest import ARC62_CONFIG_DELETED, ARC62_CONFIG_UPDATED


def test_pass_deploy(circulating_supply_client: CirculatingSupplyClient) -> None:
    configs = circulating_supply_client.state.box.get_all()
    assert not configs


def test_pass_arc28_events_spec(
    circulating_supply_client: CirculatingSupplyClient,
) -> None:
    signatures = {
        f"{event.name}({','.join(arg.type for arg in event.args)})"
        for event in circulating_supply_client.app_spec.events or []
    }
    assert signatures == {ARC62_CONFIG_UPDATED, ARC62_CONFIG_DELETED}
