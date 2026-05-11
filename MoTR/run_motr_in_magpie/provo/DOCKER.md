# MoTR Experiment - Docker Setup

## Build și rulare

### 1. Build Docker image
```bash
cd MoTR/run_motr_in_magpie/provo
docker build -t motr-experiment .
```

### 2. Rulează containerul
```bash
docker run -d -p 8080:80 --name motr-app motr-experiment
```

### 3. Accesează aplicația
Deschide browser-ul la: `http://localhost:8080`

## Comenzi utile

### Oprește containerul
```bash
docker stop motr-app
```

### Șterge containerul
```bash
docker rm motr-app
```

### Vezi logs
```bash
docker logs motr-app
docker logs -f motr-app  # follow logs
```

### Rebuild și restart (după modificări)
```bash
docker stop motr-app && docker rm motr-app && docker build -t motr-experiment . && docker run -d -p 8080:80 --name motr-app motr-experiment
```

### Vezi containerele active
```bash
docker ps
```

### Intră în container (pentru debugging)
```bash
docker exec -it motr-app sh
```

## Structura

- **Dockerfile** - Configurația Docker cu build multi-stage
- **nginx.conf** - Configurația Nginx pentru serving Vue.js SPA
- **.dockerignore** - Fișiere excluse din build

## Port-uri

- **80** - Portul intern al containerului (nginx)
- **8080** - Portul extern pe host (poți schimba cu `-p 3000:80` de exemplu)
