<script lang="ts">
	import { onDestroy } from 'svelte';
	import { digitalTwinsService } from '$lib/config/config';
	export let digitalTwinId: string;

	let commands: any[] = [];
	let showForm = false;
	let sending = false;
	let error = '';
	let form = { action: 'stop' as 'start' | 'stop', value: 10, duration: 6 };

	const TYPE_LABEL: Record<string, string> = { irrigation: 'Riego', water: 'Riego' };
	const ACTION_LABEL: Record<string, string> = { stop: 'Parar riego', start: 'Iniciar riego' };

	async function load(id: string) {
		try {
			const result = await digitalTwinsService.getCommands(id);
			// La respuesta puede ser null si el gemelo aún no tiene comandos
			if (id === digitalTwinId) commands = result ?? [];
		} catch (e) {
			if (id === digitalTwinId) commands = [];
		}
	}

	// Recarga al cambiar de gemelo y cada 5 s, para que los comandos automáticos (watcher)
	// aparezcan sin tener que refrescar la página
	$: if (digitalTwinId) load(digitalTwinId);
	const timer = setInterval(() => digitalTwinId && load(digitalTwinId), 5000);
	onDestroy(() => clearInterval(timer));

	const elapsedHours = (c: any) => (Date.now() - new Date(c.Timestamp).getTime()) / 3600000;
	const remainingHours = (c: any) => Math.max(0, Number(c.duration) - elapsedHours(c));

	async function submit() {
		error = '';
		sending = true;
		try {
			await digitalTwinsService.createCommand(digitalTwinId, {
				type: 'irrigation',
				action: form.action,
				value: Number(form.value),
				unit: 'mm',
				duration: Math.round(Number(form.duration))
			});
			showForm = false;
			await load(digitalTwinId);
		} catch (e) {
			error = 'No se pudo crear el comando. Revisa los valores e inténtalo de nuevo.';
		} finally {
			sending = false;
		}
	}
</script>

<section class="card">
	<h1>Comandos</h1>
	{#if !showForm}
		<button class="button button-primary" on:click={() => (showForm = true)}>
			Generar un nuevo comando
		</button>
	{:else}
		<form class="new-command" on:submit|preventDefault={submit}>
			<h3 class="m-0">Nuevo comando de riego</h3>
			<label>
				Acción
				<select bind:value={form.action}>
					<option value="stop">Parar riego</option>
					<option value="start">Iniciar riego</option>
				</select>
			</label>
			<label>
				Cantidad de agua (mm)
				<input type="number" min="0" step="0.5" bind:value={form.value} required />
			</label>
			<label>
				Duración (horas)
				<input type="number" min="1" max="168" step="1" bind:value={form.duration} required />
			</label>
			{#if error}<p class="error m-0">{error}</p>{/if}
			<div class="buttons">
				<button class="button button-primary" type="submit" disabled={sending}>
					{sending ? 'Enviando...' : 'Enviar comando'}
				</button>
				<button class="button" type="button" on:click={() => (showForm = false)}>Cancelar</button>
			</div>
		</form>
	{/if}
	<hr />
	<h3 class="m-0">Historial de comandos</h3>
	{#if commands.length === 0}
		Nada por aquí ...
	{:else}
		<div class="commands-scroll">
			{#each commands as command}
				<div class="card-inner">
					<h3 class="m-0">
						{(TYPE_LABEL[command.type] ?? command.type).toUpperCase()} - {command.automated
							? 'Automático'
							: 'Manual'}
					</h3>
					<p class="m-0">
						<strong>
							{new Date(command.Timestamp).toLocaleString('es-ES', {
								dateStyle: 'short',
								timeStyle: 'short'
							})}
						</strong>
					</p>
					<p class="m-0">Acción: {ACTION_LABEL[command.action] ?? command.action}</p>
					<p class="m-0">Durante: {command.duration} horas</p>
					<p class="m-0">Quedan: {remainingHours(command).toFixed(1)} horas</p>
					<div
						class="badge"
						style="background-color: {remainingHours(command) > 0 ? '#88e4ff' : '#88ffc7'}"
					>
						{remainingHours(command) > 0 ? 'En curso' : 'Completado'}
					</div>
					<h2 class="m-0">{Number(command.value).toFixed(2)} {command.unit}</h2>
				</div>
			{/each}
		</div>
	{/if}
</section>

<style lang="scss">
	section {
		display: flex;
		flex-direction: column;
		align-items: center;
		max-height: 75vh;
	}

	.card-inner {
		width: 90%;
		position: relative;
	}

	.commands-scroll {
		overflow: scroll;
		width: 100%;
		display: grid;
		row-gap: 0.5rem;
		justify-items: center;
	}

	hr {
		width: 80%;
	}

	h2 {
		position: absolute;
		top: 50px;
		right: 20px;
		margin: 0;
	}

	.badge {
		font-size: 15px;
		position: absolute;
		top: 80px;
		right: 10px;
	}

	.new-command {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		width: 90%;

		label {
			display: flex;
			flex-direction: column;
			gap: 0.2rem;
			font-size: 0.9rem;
		}

		.buttons {
			display: flex;
			gap: 0.5rem;
		}

		.error {
			color: #c0392b;
			font-size: 0.85rem;
		}
	}
</style>
