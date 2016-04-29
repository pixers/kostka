from functools import wraps
import pkg_resources

def extensible_command(f):
    if hasattr(extensible_command, 'current_group'):
        ep_group = extensible_command.current_group
    else:
        ep_group = 'kostka'

    ep_group += '.' + f.__name__

    extensions = []
    extensible_command.current_group = ep_group
    for ep in pkg_resources.iter_entry_points(group=ep_group):
        extensible_command.current_group = ep_group
        extension = ep.load()
        if hasattr(extension, '__click_params__'):
            f.__click_params__ += extension.__click_params__
        extensions.append(extension)

    del extensible_command.current_group

    def exec_extensions(*args, **kwargs):
        for extension in extensions:
            extension(*args, **kwargs)

    @wraps(f)
    def inner(*args, **kwargs):
        return f(*args, extensions=exec_extensions, **kwargs)

    return inner

def extend_with(group):
    def inner(cls):
        for ep in pkg_resources.iter_entry_points(group=group):
            cls.__bases__ += (ep.load(),)

        return cls

    return inner
