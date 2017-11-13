# F5 BIG-IP plugin

This plugin provides functionality for interacting with F5 BIG-IP.

Currently available functionality:

* Synchronizing a BIG-IP cluster

## Node Types

### `cloudify.bigip.BigIP`

Represents a BIG-IP installation and holds information pertaining to how to connect to it.

At the moment, BIG-IP's lifecycle orchestration is not supported. The only operation
supported is `sync`, which accepts a `sync_group` and synchronizes the BIG-IP sync cluster
by that name.

This operation is not a part of the BIG-IP lifecycle, but exists on a custom interface; to invoke it, you can use the `execute_operation` workflow, passing a payload such as the following:

```yaml
operation: cluster.operations.sync
operation_kwargs:
  sync_group: my_sync_group
type_names: [cloudify.bigip.BigIP]
```

This will invoke the `cluster.operations.sync` operation on all node templates in the blueprint that belong to the type `cloudify.big.BigIP`. You can also specify `node_ids` instead of `type_names` in order to address a particular node template; see the documentation for the `execute_operation` built-in workflow.
