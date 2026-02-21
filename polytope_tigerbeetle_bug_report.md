# Bug Report / Feature Request: Support for Privileged Containers and Custom Security Profiles in `polytope/container`

## Summary
Currently, there is no way to run the TigerBeetle database (`ghcr.io/tigerbeetle/tigerbeetle`) locally on macOS Docker environments using the `polytope/container` tool. 

TigerBeetle has a hard dependency on the Linux `io_uring` subsystem for its high-performance asynchronous I/O. However, the default Docker `seccomp` profile blocks `io_uring` syscalls. The standard Docker solution is to run the container using `--security-opt seccomp=unconfined` or `--privileged`.

Because `polytope/container` does not expose options for setting custom container security profiles or running containers in privileged mode, it is structurally impossible to start TigerBeetle via a standard `polytope.yml` workflow on macOS. In-container workarounds (such as altering the `entrypoint` to run `sysctl kernel.io_uring_disabled=0`) also fail because modifying `sysctl` requires host kernel privileges that the container lacks.

## Reproducing the Issue

1. Create a `services/tigerbeetle/polytope.yml` configuring TigerBeetle using `polytope/container`:
```yaml
tools:
  tigerbeetle:
    info: Runs the TigerBeetle database cluster
    run:
      - tool: polytope/container
        args:
          image: ghcr.io/tigerbeetle/tigerbeetle:latest
          id: tigerbeetle
          mounts:
            - { path: /data, source: { type: volume, scope: project, id: tigerbeetle-data } }
          cmd:
            - start
            - --addresses=0.0.0.0:3000
            - /data/0.tigerbeetle
          create: always
```

2. Run the tool via Polytope on a macOS environment with Docker Desktop or OrbStack.

3. Check the container logs. TigerBeetle will fail to start with the following error:
```
error(io): io_uring is not available
error(io): likely cause: the syscall is disabled by sysctl, try 'sysctl -w kernel.io_uring_disabled=0'
error: PermissionDenied
```

## Investigation Details & Why Workarounds Fail
To mitigate the `io_uring` error, we investigated manipulating the `mounts`, `cmd`, and `entrypoint` args within `polytope.yml`, as well as creating a custom wrapper image:

1. **Host `sysctl` Configuration**: While OrbStack and Docker Desktop Linux VMs often have `io_uring` enabled at the VM level, Docker's default `seccomp` profile filters the syscalls out for unprivileged containers.
2. **Container `sysctl` Workarounds**: We attempted to modify the entrypoint to run `sysctl -w kernel.io_uring_disabled=0` before starting TigerBeetle. However, because unprivileged containers run with a read-only sysfs and lack `CAP_SYS_ADMIN`, the `sysctl` command fails with either a `Read-only file system` or `Permission denied` error.
3. **Missing CLI Arguments**: When inspecting the available arguments for the `polytope/container` tool (`pt tools get polytope/container`), there are no mappings for Docker's `--privileged`, `--cap-add`, or `--security-opt` flags.

As a result, as long as TigerBeetle runs as an unprivileged container bound by Docker's default `seccomp` profile, it cannot execute the required `io_uring` syscalls.

## Proposed Solution / Feature Request
To support modern, high-performance databases like TigerBeetle and ScyllaDB (which also heavily relies on `io_uring`), the `polytope/container` tool needs to expose arguments that map to Docker container security primitives.

Specifically, adding support for the following arguments in `polytope/container` would resolve the issue:
1. `privileged: bool` - Maps to Docker's `--privileged` flag.
2. `security-opts: [str]` - Maps to Docker's `--security-opt` flag (e.g., `seccomp=unconfined`).
3. `cap-add: [str]` and `cap-drop: [str]` - Maps to Docker's `--cap-add` and `--cap-drop` flags (useful for fine-grained capability tuning like `CAP_IPC_LOCK` which TigerBeetle also benefits from).

Without these configurations, teams using Polytope must resort to breaking their orchestration paradigm and managing specific services manually via standalone `docker-compose` files.
