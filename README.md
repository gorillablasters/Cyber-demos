
# Operation Doomsday – MF DOOM Groundstation CTF Stack

This stack runs three services:

- **doomsat** – the simulated satellite / embedded device (TCP on 7000)
- **backend** – FastAPI groundstation API proxying commands to doomsat
- **frontend** – Next.js MF DOOM–themed groundstation UI

## Quick start

```bash
docker-compose up --build
```

Then open the UI:

- Frontend: http://localhost:3000
- Backend (API): http://localhost:8000 (usually not needed directly)
- DOOMSAT raw port (for debugging): localhost:7000

## In the UI

- Use the console to type commands like:
  - `help`
  - `dump 0 512`
  - `leak`
  - `fw_info`
- Use `/firmware` page to upload a crafted firmware image.

Flags are embedded in:

- doomsat/memory/flags/*
- doomsat/memory/flash.bin (created at runtime)

This is meant as a base you can tweak for your CTF.
