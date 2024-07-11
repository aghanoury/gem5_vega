# Gem5 with AMD VEGA GPU

> warning. things are changing quickly in this repo. stay tuned for more updates

Here, we are using gem5 plus the [AMD GPU model](https://www.gem5.org/documentation/general_docs/gpu_models/vega). Due to strict library dependencies/requirements for running VEGA, we simply run everything in a container using a 'prebuilt' docker image.

To compile gem5 or execute a binary, we leverage a containerized environment.  The source files reside on the host machine and are dynamically mounted into the Docker container for each compilation or execution.

## Setup

This [tutorial](https://www.gem5.org/2020/05/27/modern-gpu-applications.html) provides a useful starting point for building the Docker image you'll need. However, if you are working on the `georgia` system, a pre-built Docker image named `amd_gpu` is already available. This image was created around March 2024, so it might become outdated in the future and require rebuilding with the latest components. For now, you can use the existing image without any concerns.

The `amd_gpu` container is specifically designed to support AMD Vega GPU applications. It does not include the gem5 repository or any CUDA library support. Therefore, you need to clone both the gem5 and gem5-resources repositories at the top level of your working directory:

```sh
git clone https://github.com/gem5/gem5
git clone https://github.com/gem5/gem5-resources.git
```

Throughout the remainder of this documentation, we will assume the user has the following file structure
```sh
tree -L 2

# output:
.
├── bench
│   ├── gem5-resources
│   ├── gpu-rodinia
│   └── polybench-2.0
├── env.sh
├── gem5
│   ├── build
	...
...
```

When building or running benchmarks, you will invoke Docker and mount your current directory into a directory within the container. The specific commands for this process are explained below.

## Running

As explained previously, each command is run in a docker context. Essentially, we just prepend any normal gem5 command with the docker setup command. I have created a script to make this easier, `rundockercmd`, which is explained below.

### Docker
We typically run the following command to build gem5.
```sh
source env.sh
cd gem5
scons -sQ -j$(nproc) build/GCN3_X86/gem5.opt
```
However, since we need to do this in docker, we prepend this command with the docker setup:
```sh
cd gem5
docker run --rm -u $UID:$GID -v $(pwd):$(pwd) -w $(pwd) amd_gpu scons -sQ -j$(nproc) build/GCN3_X86/gem5.opt
```
The key thing here is the `-v` option which is mounting our current working directory and also creating an identical path and the `-w` which sets our docker current working directory to that path (because the default cwd is `/`). Ask an LLM for more information.

To simplify this process, I have written a basic script, `rundockermcd` which essentially runs this every time, plus mounting a few other important directories. To use it, first `source env.sh` which sets up some global paths. Then, we're free to use `rundockercmd` anywhere. The command will always mount the gem5 root directory and benchmark directory. 

```sh
cd gem5
rundockercmd scons -j$(nproc) build/GCN3_X86/gem5.opt
```

> NOTE: If you run into any errors regarding read/write permissions, message Pooya for more help.

### Running GPU Benchmarks

Use the `rundockercmd` to run GPU applications. Here's an example on how to run the `pennant` benchmark, assuming a file tree that looks like this:

```sh
rundockercmd gem5/build/GCN3_X86/gem5.opt gem5/configs/example/apu_se.py -n3 --benchmark-root=bench/gem5-resources/src/gpu/pennant/build -cpennant --options="bench/gem5-resources/src/gpu/pennant/test/noh/noh.pnt"
```

This was a GPU benchmark that was included with the in the `gem5-resources`. You can find more of them [here](https://github.com/gem5/gem5-resources/tree/stable/src/gpu). Each benchmark should have some `readme` explaining instructions on how to compile and then run. 

> NOTE: each benchmark's instructions to compile may need to be tweaked to run in our framework, namely, the docker command they use before their compile command may differ from ours. 
> Also note that some commands use quotes `"` around some of their arguments. When using `rundockercmd`, you should backslash each quotation mark `\"` 


### Running all benchmarks
I have convert our old script for running all spec benchmarks in parallel with live statuses to one which runs all of the gem5-resources benchmarks. 
```sh
source env.sh # make sure to source this be

```