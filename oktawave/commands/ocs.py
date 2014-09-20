import click
from oktawave.commands.context import pass_context, OktawaveCliGroup, positional_option


def container_param(*args, **kwargs):
    kwargs.setdefault('help', 'container name')
    return positional_option(*args, **kwargs)

def path_param(*args, **kwargs):
    kwargs.setdefault('help', 'path inside container')
    return positional_option(*args, **kwargs)


def ocs_split_params(container, path):
    if path is None:
        container, _slash, path = container.partition('/')
        if path == '':
            path = None
    return container, path


def swift_object_type(data):
    if data['content_type'] == 'application/directory':
        return 'directory'
    if data['content_type'] == 'application/object':
        return 'object'
    return data['content_type']


def list_swift_objects(ctx, container, cname, path=None):
    if path is None:
        path = ''
    elif not path.endswith('/'):
        path += '/'
    container = container[1]

    if path:
        for d in container:
            if d['content_type'] == 'application/directory' and d['name'] + '/' == path:
                print 'Directory content:'
                break
        else:
            print "No such container/directory!"
            return
    else:
        print 'Container content:'

    def fmt_file(swift_obj):
        return [
            cname + '/' + swift_obj['name'],
            swift_object_type(swift_obj),
            swift_obj['bytes'],
            swift_obj['last_modified'],
        ]

    ctx.print_table(
        ['Full path', 'Type', 'Size in bytes', 'Last modified'],
        sorted([o for o in container if o['name'].startswith(path)], key=lambda row: row['name']),
        fmt_file)


def print_swift_file(ctx, data):
    headers, content = data
    ctype = headers['content-type']

    if ctype == 'application/directory':
        print '<DIRECTORY>'
    elif ctype == 'application/object':
        attrs = dict((key[len('x-object-meta-'):], headers[key])
                     for key in headers if key.startswith('x-object-meta-'))
        ctx.p.print_table([['Key', 'Value']] + [[
            key, attrs[key]
        ] for key in sorted(attrs.keys(), key=lambda x: x.lower())])
    else:
        print content


@click.group(cls=OktawaveCliGroup, name='OCS')
def OCS():
    """Manage OCS containers"""
    pass


@OCS.command()
@pass_context
def OCS_ListContainers(self):
    """List OCS containers"""
    headers, containers = self.ocs.get_account()
    self.p.print_hash_table(
        dict((o['name'], [o['count'], o['bytes']]) for o in containers),
        ['Container name', 'Objects count', 'Size in bytes']
    )


@OCS.command(epilog="Container and path may be specified as a single argument as container/path")
@container_param('container')
@path_param('path', required=False)
@pass_context
def OCS_List(ctx, container, path):
    """List content of a directory or container"""
    container, path = ocs_split_params(container, path)
    obj = ctx.ocs.get_container(
        container)  # TODO: perhaps we can optimize it not to download the whole container when not necessary
    list_swift_objects(ctx, obj, container, path)


@OCS.command(epilog="Container and path may be specified as a single argument as container/path")
@container_param('container')
@path_param('path', required=False)
@pass_context
def OCS_Get(ctx, container, path):
    """Get an object or file"""
    container, path = ocs_split_params(container, path)
    if path is None:
        headers, contents = ctx.ocs.get_container(container)
        ctx.p.print_hash_table(
            {
                '1 Container name': [container],
                '2 Objects count': [headers['x-container-object-count']],
                '3 Size in bytes': [headers['x-container-bytes-used']],
            },
            order=True)
    else:
        print_swift_file(ctx, ctx.ocs.get_object(container, path))


@OCS.command()
@container_param('name')
@pass_context
def OCS_CreateContainer(ctx, name):
    """Creates a new container"""
    ctx.ocs.put_container(name)
    print "OK"


@OCS.command()
@container_param('container')
@path_param('path')
@positional_option('local_path', type=click.File('rb'), help='file to upload')
@pass_context
def OCS_Put(ctx, container, path, local_path):
    """Upload a file to OCS"""
    ctx.ocs.put_object(container, path, local_path)
    print "OK"


@OCS.command(epilog="Container and path may be specified as a single argument as container/path")
@container_param('container')
@path_param('path', required=False)
@pass_context
def OCS_Delete(ctx, container, path):
    """Delete an object from the container"""
    container, path = ocs_split_params(container, path)
    ctx.ocs.delete_object(container, path)
    print "OK"


@OCS.command()
@container_param('name')
@pass_context
def OCS_DeleteContainer(ctx, name):
    """Delete a container"""
    ctx.ocs.delete_container(name)
    print "OK"

