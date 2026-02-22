# installation 
helm upgrade --install AeroFoil ./ -n namespace -f values.yaml

# Optional: add a dedicated SSD-backed mount (for example `/app/conversion-tmp`)
# and set `library.conversion_staging_dir` in settings to reduce conversion IO on library volumes.
