"""Repository layer for file-backed app data and generated game data."""

from .base_repository import BaseRepository, get_default_base_repository
from .config_repository import (
    get_config_value,
    set_config_value,
    get_saved_league,
    get_saved_stash_id,
    save_client_id,
    save_user_agent,
    save_league,
    save_stash_id,
)
from .loadout_repository import (
    load_all_loadouts,
    save_all_loadouts,
    migrate_loadout_to_slot_dict,
    reconstruct_filters_from_active_mod_groups_state,
)
