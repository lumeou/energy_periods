from abc import ABC, abstractmethod

# Registro de providers disponibles
PROVIDERS = {}

def register_provider(name):
    def wrapper(cls):
        PROVIDERS[name] = cls
        return cls
    return wrapper


def get_provider(provider_type, config):
    if provider_type not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider_type}")

    return PROVIDERS[provider_type](**config)


# Interfaz base
class BaseHolidayProvider(ABC):

    def __init__(self, tag=None):
        self.tag = tag

    @abstractmethod
    async def get_holidays(self):
        """
        Returns:
            dict[str, set[str]]
            {
                "2026-01-01": {"national"},
                "2026-03-19": {"regional"}
            }
        """
        pass
