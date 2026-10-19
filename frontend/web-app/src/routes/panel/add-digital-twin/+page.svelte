<script lang="ts">
	import { goto } from '$app/navigation';
	import MapInd from '$lib/components/panel/MapInd.svelte';
	import { digitalTwinsService } from '$lib/config/config';
	import { user } from '$lib/config/stores/user';

	const createNewDigitalTwin = async (e: Event) => {
		e.preventDefault();
		// Get user information
		const { id } = $user;
		try {
			// Add id to digital twin
			let parsedDigitalTwin = JSON.parse(digitalTwin);
			parsedDigitalTwin.properties.userId = id;
			await digitalTwinsService.createNewDigitalTwin(parsedDigitalTwin);
			// Refresh page
			goto('/panel');
		} catch (error) {
			alert('Error al crear el gemelo digital');
		}
	};

	let digitalTwin = `{
  "crs": {
      "type": "EPSG",
      "properties": {
        "code": "4258"
      }
    },
    "geometry": {
      "type": "Polygon",
      "coordinates": [
        [
          [0.87729827, 41.74318963],
          [0.87680735, 41.74320183],
          [0.87675267, 41.74698142],
          [0.87688907, 41.7469771],
          [0.87729992, 41.74696164],
          [0.87729827, 41.74318963]
        ]
      ]
    },
    "properties": {
      "location": {
        "province": "LLEIDA",
        "city": "BELLCAIRE D'URGELL",
        "municipality": "BELLCAIRE D'URGELL",
        "geographicSpot": "BELLCAIRE D'URGELL",
        "ccaa": "CATALUÑA"
      },
      "crop": {
        "id": "",
        "name": "ALFALFA",
        "varietyId": "",
        "variety": ""
      },
      "slope": 12,
      "area": 1.8104,
      "areaSIGPAC": 1.8104,
      "parcelUse": "TA",
      "irrigationCoef": 100,
      "admisibility": 0,
      "rainfedOrIrrigated": "Irrigated"
    },
    "type": "Feature",
    "id": "25-56-0-0-8-162-1",
    "year": 2024
}`;

	let formatedGeojson = '';

	$: {
		try {
			formatedGeojson = JSON.parse(digitalTwin);
		} catch (error) {
			formatedGeojson = '';
		}
	}
</script>

<h1>Crear nuevo gemelo digital</h1>
<p>Introduce el GeoJSON asociado a la parcela para crear un nuevo gemelo digital</p>
<section>
	<form on:submit|preventDefault={createNewDigitalTwin}>
		<label for="geojson">Introduce el GeoJSON asociado a la parcela</label>
		<!-- Restrict manual size adjust -->
		<textarea id="geojson" name="geojson" rows="30" cols="50" bind:value={digitalTwin}></textarea>
		<button type="submit">Crear</button>
		<!-- {digitalTwin} -->
	</form>
	<div style="height: 670px; max-width: 500px; width: 500px;">
		{#if digitalTwin}
			<MapInd digitalTwin={formatedGeojson} />
		{:else}
			<p>Introduce el GeoJSON asociado a la parcela para crear un nuevo gemelo digital</p>
		{/if}
	</div>
</section>

<style lang="scss">
	h1 {
		margin-top: 0;
	}

	section {
		display: flex;
		flex-direction: row;
		justify-content: center;
		height: 100%;
		flex-wrap: wrap;
		gap: 1rem;
		padding-top: 2rem;
	}

	form {
		display: flex;
		flex-direction: column;
		align-items: center;
		row-gap: 0.5rem;
	}
</style>
