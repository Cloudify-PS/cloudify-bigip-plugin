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


### `cloudify.nodes.bigip.gtm.DNSLoadBalancer`

Represents a DNS Load Balancer that is responsible for creating the following resources:

1. Virtual Server
2. Server Pool
3. Wide IP (A Records)


The only lifecycle actions that are supported: Creation and Deletion

This is how to define a GTM Load Balancer

```
  gtm_load_balancer:
    type: cloudify.nodes.bigip.gtm.DNSLoadBalancer
    properties:
      ip: { get_input: gtm_ip }
      user: { get_input: gtm_user }
      password: { get_input: gtm_password }
      partition: { get_input: gtm_partition }
      record_type: { get_input: gtm_record_type }
      gtm_server: { get_input: gtm_server_name }
      virtual_server_config:
        kwargs: { get_input: gtm_virtual_server_config }
      pool_config:
        kwargs: { get_input: gtm_pool_config }
      pool_member_config:
        kwargs: { get_input: gtm_pool_member_config }
      wip_config:
        kwargs: { get_input: gtm_wip_config }
```

The inputs can be provided in a separate input file as described on the template `examples/gtm-blueprint-inputs.yaml.template`

`examples/gtm-blueprint.yaml` is an example provided for how to create a GTM Load Balancer

