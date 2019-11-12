# Trek

My own personal utility for mapping out modem signal and GPS data.

## Usage

First, make sure the dependencies are installed:

```sh
pip3 install -r requirements.txt
```

Now, after you've connected your modem and GPS, run:

```sh
python3 trek.py
```

This will automatically start logging to `data.log` and start drawing the UI.

## Notes

Right now this runs on my Macbook and is good enough for what I need. I don't have any immediate plans to generalize it, but feel to pick out any parts that are useful to you.
