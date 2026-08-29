.PHONY: install test lint dry-run clean

install:
	pip install -r requirements.txt
	pip install -e .

test:
	python -m pytest -q

lint:
	python -m pyflakes wifi_evil_twin || true

# Show exactly what the toolkit would do, without any hardware.
dry-run:
	python -m wifi_evil_twin run --ssid Free-WiFi --interface wlan0 \
		--deauth --deauth-bssid 00:11:22:33:44:55 --dry-run

clean:
	rm -rf data captures .wet_ack *.log
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
