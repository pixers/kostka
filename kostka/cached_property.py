class cached_property(property):
    def __init__(self, fget=None, fset=None, fdel=None, doc=None, **kwargs):
        self.cached_value = {}
        if fget:
            if hasattr(fget, '__self__') and fget.__self__.__class__ == self.__class__:
                fget = fget.__self__._fget
            self._fget = fget
            fget = self.fget_wrapper

        if fset and fset != self.fset_wrapper:
            if hasattr(fset, '__self__') and fset.__self__.__class__ == self.__class__:
                fset = fset.__self__._fset
            self._fset = fset
            fset = self.fset_wrapper

        super().__init__(fget=fget, fset=fset, fdel=None, doc=None, **kwargs)

    def fget_wrapper(self, obj, *args, **kwargs):
        if not hasattr(obj, '_cached_values'):
            obj._cached_values = {}

        name = self._fget.__name__

        if name in obj._cached_values:
            return obj._cached_values[name]
        else:
            obj._cached_values[name] = self._fget(obj, *args, **kwargs)
            return obj._cached_values[name]

    def fset_wrapper(self, obj, *args, **kwargs):
        if not hasattr(obj, '_cached_values'):
            obj._cached_values = {}

        name = self._fget.__name__
        obj._cached_values[name] = self._fset(obj, *args, **kwargs)
        return obj._cached_values[name]
