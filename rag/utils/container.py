"""
Dependency Injection Container for Agentic RAG system.

Provides centralized service registration and retrieval.
"""
import logging
from typing import Any, Dict, Optional, Type

logger = logging.getLogger(__name__)


class Container:
    """
    Simple dependency injection container.

    Usage:
        container = Container()
        container.register('embedding', EmbeddingService)
        service = container.get('embedding')
    """

    _instance: Optional['Container'] = None
    _services: Dict[str, Any]

    def __new__(cls) -> 'Container':
        """Singleton pattern - only one container instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services = {}
        return cls._instance

    def register(self, name: str, service: Any, override: bool = False) -> None:
        """
        Register a service instance.

        Args:
            name: Service name/identifier
            service: Service instance or class
            override: Allow overriding existing registrations
        """
        if name in self._services and not override:
            logger.warning(f'Service "{name}" already registered, skipping')
            return

        self._services[name] = service
        logger.debug(f'Registered service: {name}')

    def register_factory(self, name: str, factory: callable, override: bool = False) -> None:
        """
        Register a factory function for lazy instantiation.

        Args:
            name: Service name
            factory: Callable that returns a service instance
        """
        if name in self._services and not override:
            logger.warning(f'Service "{name}" already registered, skipping')
            return

        self._services[name] = {'type': 'factory', 'factory': factory}
        logger.debug(f'Registered factory: {name}')

    def get(self, name: str) -> Optional[Any]:
        """
        Get a service instance by name.

        Args:
            name: Service name

        Returns:
            Service instance or None if not found
        """
        service = self._services.get(name)
        if service is None:
            logger.warning(f'Service "{name}" not found')
            return None

        # Instantiate factory if needed
        if isinstance(service, dict) and service.get('type') == 'factory':
            factory = service['factory']
            instance = factory()
            # Cache the instance
            self._services[name] = instance
            return instance

        return service

    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services

    def clear(self) -> None:
        """Clear all registrations."""
        self._services.clear()
        logger.debug('Cleared all services')

    def list_services(self) -> list:
        """List all registered service names."""
        return list(self._services.keys())


# Global container instance
container = Container()
