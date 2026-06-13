let googleMapInstance = null;
let googleMarkerInstance = null;
let googleAutocomplete = null;

const STORE_LOCATION = { lat: -1.3979704, lng: 36.7670994 };
const RATE_PER_KM = 10;
const FREE_DELIVERY_THRESHOLD = 20000;

function checkoutApp() {
    return {
        open: false,
        step: 1,
        phone: '',
        email: '',
        searchQuery: '',
        suggestions: [],
        selectedLocation: null,
        showCurrentLocationOption: false,
        locationLoading: false,
        deliveryAvailable: null,
        deliveryDistance: 0,
        deliveryFee: 0,
        freeDelivery: false,
        // Ensure this works based on my file structure (inline vs external CSS)
        cartTotal: typeof window !== 'undefined' && window.cartTotalAmount ? window.cartTotalAmount : 0, 
        
        calculateDistance(lat1, lon1, lat2, lon2) {
            const R = 6371;
            const dLat = (lat2 - lat1) * Math.PI / 180;
            const dLon = (lon2 - lon1) * Math.PI / 180;
            const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                      Math.sin(dLon/2) * Math.sin(dLon/2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            return R * c;
        },
        
        calculateDeliveryFee(location) {
            if (!location || !location.lat || !location.lon) return;
            
            const isKenya = this.isLocationInKenya(location);
            console.log('Location:', location);
            console.log('Is Kenya:', isKenya);
            this.deliveryAvailable = isKenya;
            
            if (!isKenya) {
                this.deliveryDistance = 0;
                this.deliveryFee = 0;
                this.freeDelivery = false;
                return;
            }
            
            const distance = this.calculateDistance(
                STORE_LOCATION.lat, STORE_LOCATION.lng,
                parseFloat(location.lat), parseFloat(location.lon)
            );
            
            this.deliveryDistance = Math.ceil(distance);
            
            if (this.deliveryDistance <= 1) {
                this.deliveryFee = 0;
            } else {
                this.deliveryFee = this.deliveryDistance * RATE_PER_KM;
            }
            
            this.freeDelivery = this.cartTotal >= FREE_DELIVERY_THRESHOLD;
        },
        
        isLocationInKenya(location) {
            if (!location) {
                console.log('No location provided');
                return false;
            }
            
            console.log('Checking location:', {
                country: location.country,
                country_short: location.country_short,
                display_name: location.display_name,
                lat: location.lat,
                lon: location.lon
            });
            
            if (location.country) {
                const country = location.country.toLowerCase().trim();
                const countryShort = location.country_short ? location.country_short.toLowerCase().trim() : '';
                console.log('Country check:', country, countryShort);
                if (country === 'kenya' || countryShort === 'ke') {
                    console.log('Matched by country name');
                    return true;
                }
                console.log('Country did not match Kenya');
                return false;
            }
            
            if (location.display_name) {
                const name = location.display_name.toLowerCase();
                console.log('Checking display_name for kenya:', name);
                if (name.includes('kenya')) {
                    console.log('Matched by display_name');
                    return true;
                }
            }
            
            const lat = parseFloat(location.lat);
            const lon = parseFloat(location.lon);
            
            if (!isNaN(lat) && !isNaN(lon)) {
                const inKenyaBounds = lat >= -4.7 && lat <= 5.5 && lon >= 33.9 && lon <= 41.9;
                console.log('Coordinate check:', { lat, lon, inKenyaBounds });
                if (inKenyaBounds) {
                    console.log('Matched by coordinates');
                    return true;
                }
            }
            
            console.log('No match found - NOT in Kenya');
            return false;
        },
        
        handleNextClick() {
            if (!this.selectedLocation) {
                alert('Please select a location on the map');
                return;
            }
            if (this.deliveryAvailable === false) {
                alert('Delivery is not available for this location. We only deliver within Kenya.');
                return;
            }
            if (!document.getElementById('shippingForm').checkValidity()) {
                alert('Please fill in all required fields');
                return;
            }
            this.step = 2;
        },
        
        getShortLocation(location) {
            if (!location) return '';
            if (location.short_name) return location.short_name;
            if (location.area && location.county) return `${location.area}, ${location.county}`;
            if (!location.display_name) return '';
            const parts = location.display_name.split(',').slice(0, 2);
            return parts.join(', ');
        },
        
        formatLocation(data) {
            const addr = data.address || {};
            const area = addr.suburb || addr.village || addr.town || addr.neighbourhood || addr.residential || addr.city_district || addr.road || '';
            const county = addr.county || addr.state_district || addr.state || '';
            
            let shortName = '';
            if (area && county) {
                shortName = `${area}, ${county}`;
            } else if (area) {
                shortName = area;
            } else if (county) {
                shortName = county;
            } else {
                shortName = data.display_name.split(',').slice(0, 2).join(', ');
            }
            
            return {
                display_name: data.display_name,
                short_name: shortName,
                area: area,
                county: county,
                lat: data.lat,
                lon: data.lon,
                place_id: data.place_id
            };
        },
        
        init() {
            this.$watch('open', (value) => {
                if (value) {
                    
                    setTimeout(() => {
                        this.initGoogleMap();
                    }, 400);
                }
            });
        },
        
        initGoogleMap() {
            if (googleMapInstance) return;
            if (typeof google === 'undefined' || !google.maps) {
                console.error('Google Maps API not loaded. Check your API key.');
                return;
            }
            
            const mapDiv = document.getElementById('google-map');
            if (!mapDiv) return;
            
            googleMapInstance = new google.maps.Map(mapDiv, {
                center: { lat: -1.2921, lng: 36.8219 },
                zoom: 12,
                mapTypeControl: false,
                streetViewControl: false,
                fullscreenControl: false,
                mapId: 'DEMO_MAP_ID'
            });
            
            googleMapInstance.addListener('click', async (e) => {
                const lat = e.latLng.lat();
                const lng = e.latLng.lng();
                
            
                if (googleMarkerInstance) {
                    googleMarkerInstance.map = null;
                }
                
                const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");
                googleMarkerInstance = new AdvancedMarkerElement({
                    position: { lat, lng },
                    map: googleMapInstance
                });
                
                const geocoder = new google.maps.Geocoder();
                geocoder.geocode({ location: { lat, lng } }, (results, status) => {
                    if (status === 'OK' && results[0]) {
                        const country = results[0].address_components.find(c => c.types.includes('country'));
                        this.selectedLocation = {
                            display_name: results[0].formatted_address,
                            short_name: results[0].address_components[0]?.long_name + ', ' + 
                                        results[0].address_components[1]?.long_name,
                            lat: lat,
                            lon: lng,
                            place_id: results[0].place_id,
                            country: country ? country.long_name : null,
                            country_short: country ? country.short_name : null
                        };
                        googleMarkerInstance.title = this.selectedLocation.short_name;
                        this.calculateDeliveryFee(this.selectedLocation);
                    }
                });
            });
            
            const searchInput = document.getElementById('location-search-input');
            if (searchInput && google.maps.places.PlaceAutocompleteElement) {
                try {
                    const autocompleteElement = new google.maps.places.PlaceAutocompleteElement({
                        componentRestrictions: { country: 'ke' }
                    });
                    autocompleteElement.style.cssText = 'display: block; width: 100%; --gm-place-autocomplete-input-background: white; --gm-place-autocomplete-input-color: #333; color-scheme: light;';
                    autocompleteElement.setAttribute('placeholder', 'Ongata Rongai');
                    searchInput.parentNode.insertBefore(autocompleteElement, searchInput.nextSibling);
                    searchInput.style.display = 'none';
                    
                    setTimeout(() => {
                        const input = autocompleteElement.shadowRoot?.querySelector('input');
                        const container = autocompleteElement.shadowRoot?.querySelector('.input-container');
                        if (input) {
                            input.style.cssText = 'background: white !important; color: #333 !important; border: 1px solid #ddd !important; padding: 8px 10px !important; border-radius: 4px !important; color-scheme: light !important;';
                            input.placeholder = 'Ongata Rongai';
                        }
                        if (container) {
                            container.style.background = 'white';
                        }
                    }, 100);
                    
                    autocompleteElement.addEventListener('gmp-select', async (event) => {
                        const placePrediction = event.placePrediction;
                        if (placePrediction) {
                            try {
                                const place = placePrediction.toPlace();
                                await place.fetchFields({ fields: ['displayName', 'formattedAddress', 'location', 'addressComponents'] });
                                
                                const lat = place.location.lat();
                                const lng = place.location.lng();
                                
                                googleMapInstance.setCenter({ lat, lng });
                                googleMapInstance.setZoom(15);
                                
                               
                                if (googleMarkerInstance) {
                                    googleMarkerInstance.map = null;
                                }
                                
                                const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");
                                googleMarkerInstance = new AdvancedMarkerElement({
                                    position: { lat, lng },
                                    map: googleMapInstance,
                                    title: place.displayName
                                });
                                
                                let countryName = null;
                                let countryShort = null;
                                if (place.addressComponents) {
                                    for (const comp of place.addressComponents) {
                                        if (comp.types && comp.types.includes('country')) {
                                            countryName = comp.longText;
                                            countryShort = comp.shortText;
                                            break;
                                        }
                                    }
                                }
                                
                                this.selectedLocation = {
                                    display_name: place.formattedAddress,
                                    short_name: place.displayName,
                                    lat: lat,
                                    lon: lng,
                                    place_id: place.id,
                                    country: countryName,
                                    country_short: countryShort
                                };
                                this.searchQuery = place.displayName;
                                this.calculateDeliveryFee(this.selectedLocation);
                            } catch (err) {
                                console.error('Error fetching place details:', err);
                            }
                        }
                    });
                } catch (e) {
                    console.error('PlaceAutocompleteElement error:', e);
                    searchInput.style.display = 'block';
                }
            }
        },
        
        selectLocation(suggestion) {
            this.selectedLocation = suggestion;
            this.suggestions = [];
            this.searchQuery = suggestion.short_name || suggestion.display_name.split(',').slice(0, 2).join(', ');
            this.calculateDeliveryFee(suggestion);
            
            const lat = parseFloat(suggestion.lat);
            const lon = parseFloat(suggestion.lon);
            
            console.log('Selected location:', suggestion.short_name, 'Lat:', lat, 'Lon:', lon);
            
            if (googleMapInstance && !isNaN(lat) && !isNaN(lon)) {
                googleMapInstance.setCenter({ lat, lng: lon });
                googleMapInstance.setZoom(15);
                
               
                if (googleMarkerInstance) {
                    googleMarkerInstance.map = null;
                }
                google.maps.importLibrary("marker").then(({ AdvancedMarkerElement }) => {
                    googleMarkerInstance = new AdvancedMarkerElement({
                        position: { lat, lng: lon },
                        map: googleMapInstance,
                        title: suggestion.short_name
                    });
                });
            }
        },
        
        useCurrentLocation() {
            this.showCurrentLocationOption = false;
            this.locationLoading = true;
            
            if (!navigator.geolocation) {
                alert('Geolocation is not supported by your browser');
                this.locationLoading = false;
                return;
            }
            
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;
                    
                    this.reverseGeocodeGoogle(lat, lon);
                },
                (error) => {
                    this.locationLoading = false;
                    let message = 'Unable to get your location';
                    if (error.code === error.PERMISSION_DENIED) {
                        message = 'Location permission denied. Please enable it in your browser settings.';
                    } else if (error.code === error.POSITION_UNAVAILABLE) {
                        message = 'Location information unavailable';
                    } else if (error.code === error.TIMEOUT) {
                        message = 'Location request timed out';
                    }
                    alert(message);
                },
                { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
            );
        },
        
        reverseGeocodeGoogle(lat, lon) {
            if (!googleMapInstance) {
                this.locationLoading = false;
                alert('Google Maps not initialized');
                return;
            }
            
            const geocoder = new google.maps.Geocoder();
            geocoder.geocode({ location: { lat, lng: lon } }, (results, status) => {
                this.locationLoading = false;
                if (status === 'OK' && results[0]) {
                    const country = results[0].address_components.find(c => c.types.includes('country'));
                    const location = {
                        display_name: results[0].formatted_address,
                        short_name: results[0].address_components[0]?.long_name + ', ' + 
                                    results[0].address_components[1]?.long_name,
                        lat: lat,
                        lon: lon,
                        place_id: results[0].place_id,
                        country: country ? country.long_name : null,
                        country_short: country ? country.short_name : null
                    };
                    this.selectLocation(location);
                } else {
                    alert('Could not determine your address');
                }
            });
        }
    }
}
