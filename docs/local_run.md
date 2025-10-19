# How to run sideload locally

The recommended way to deploy the app is as follows:
* deployed in a cloud VM
* sourced the mindfile from a public github repository
* using a cloud AI API provider (e.g. OpenRouter, Google, ec)

This guide explains how to optionally source the mindfile from a local folder, and how to optionally use a local AI model.

For general setup instructions, please see the main [README.md file](../README.md). This guide assumes that you already installed dependencies and set up the environment variables. 


## How to use a local mindfile

By default, the bot downloads its mindfile (the dataset for its personality and knowledge) from a remote Github repository. For local development, you can configure it to use a local directory instead.

1.  In `config.py`, set `LOCAL_MINDFILE_DIR_PATH` to the path of your local mindfile directory. Using an absolute path is recommended. For example:
    ```python
    LOCAL_MINDFILE_DIR_PATH = "/path/to/your/mindfile_dataset"
    ```

We recommend running your locally-sourced mindfile with a cloud AI API provider, as usual. 

## How to use a local AI provider (Ollama)

We strongly advise against using a local AI model, unless you have a seriosly beefy GPU and tons of RAM. Otherwise, expect to wait for hours for a response, only to get a shitty answer.

1.  **Install and run Ollama:** Follow the instructions on the [Ollama website](https://ollama.com/).

2. ** Select the model you want to use. **

As of 2025, from out tests, Gemma 3 is the least shitty model of the size less than 16 GB. But to get consistently good answers, you'll need the 27 GB version or bigger/smarter.

Aim for a model with at least 128K context window. Ideally - 1M or more.

A useful benchmark for selecting the models that are good with working with long contexts:
https://longbench2.github.io/#leaderboard

A few other relevant benchmarks worth considering:
* https://ilyagusev.github.io/ping_pong_bench/en_v2
* https://huggingface.co/spaces/cais/textquests
* https://eqbench.com/spiral-bench.html
* https://github.com/vectara/hallucination-leaderboard
* https://eqbench.com/creative_writing_longform.html
* https://livebench.ai/#/

3.  **Download a model:**
    ```bash
    ollama pull gemma3
    ```
    You can find more models on the [Ollama models page](https://ollama.com/models).

4.  **Configure the bot for Ollama:**
    -   In `config.py`, set `DEFAULT_AI_PROVIDER = "ollama"`.
    -   In `config.py`, set `OLLAMA_MODEL` to the name of the model you downloaded (e.g., `"gemma3"`).
    -   In `config.py`, set `MAX_TOKENS_ALLOWED_IN_REQUEST` to the context window size of the model you are using (e.g. for gemma3, it's 128000 ).


## Running the Bot

Once you have configured your local options, you can run the bot:

```bash
python3 main.py
```

(This guide assumes that you already installed dependencies and set up the environment variables, as per the main `README.md` file.)