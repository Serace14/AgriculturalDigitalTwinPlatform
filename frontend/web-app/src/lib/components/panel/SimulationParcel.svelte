<script lang="ts">
	// Vista cenital de parcelas de alfalfa en 5 estados (de izquierda a derecha: recién cortada,
	// rebrote, vegetativo, floración y reposo invernal). Sustituye a la imagen de árboles de la plantilla.
	// Un marco resalta la columna que se corresponde con el estado del gemelo simulado y debajo se
	// muestra el detalle (etapa, grados-día hacia el próximo corte, lluvia...).
	import img from '$lib/assets/simulation-example.jpg';

	export let status: any = null;
	// Se acepta (y se ignora) para no romper usos antiguos del componente
	export let digitalTwin: unknown = undefined;
	$: void digitalTwin;

	// Mismo valor que GDD_PER_CUT en simulations/harvest_ai_simulation.py
	const GDD_PER_CUT = 580;

	// Geometría de las columnas dentro de la imagen (fracción del ancho; ver scripts de generación)
	const MARGIN = 0.012;
	const PATH = 0.02;
	const COL_W = (1 - 2 * MARGIN - 4 * PATH) / 5;
	const colLeft = (i: number) => (MARGIN + i * (COL_W + PATH)) * 100;

	const COLUMNS = ['Corte', 'Rebrote', 'Vegetativo', 'Floración', 'Reposo'];

	$: twin = status?.digitalTwin;
	$: stage = twin?.crop_stage as string | undefined;
	$: gdd = Number(twin?.gdd_accumulated ?? 0);
	$: progress = Math.max(0, Math.min(1, gdd / GDD_PER_CUT));

	// Columna de la imagen que mejor representa el estado actual
	$: active = (() => {
		if (!twin) return -1;
		if (stage === 'Dormant') return 4;
		if (stage === 'ReadyToCut' || progress >= 0.85) return 3;
		if (progress < 0.12) return 0;
		if (progress < 0.45) return 1;
		return 2;
	})();

	const STAGE_LABEL: Record<string, string> = {
		Dormant: 'Reposo invernal',
		Growing: 'Rebrote',
		ReadyToCut: 'Listo para cortar'
	};
	$: stageLabel = stage ? (STAGE_LABEL[stage] ?? stage) : 'Sin simulación';

	$: t = status?.time;
	$: dateLabel = t ? `${t.day}/${t.month}/${t.year ?? ''}` : '--';
	$: temp = status?.weather?.temperature;
</script>

<div class="wrap">
	<div class="picture">
		<img src={img} alt="Parcelas de alfalfa en distintos estados de crecimiento" />
		{#if active >= 0}
			<div class="marker" style="left: {colLeft(active)}%; width: {COL_W * 100}%"></div>
		{/if}
	</div>
	<div class="labels">
		{#each COLUMNS as label, i}
			<span class:on={i === active} style="left: {colLeft(i)}%; width: {COL_W * 100}%">{label}</span>
		{/each}
	</div>
	<div class="info">
		<div class="row">
			<strong>{stageLabel}</strong>
			<span>{dateLabel}{temp !== undefined ? ` · ${Number(temp).toFixed(1)} °C` : ''}</span>
		</div>
		<div class="bar" title="Grados-día acumulados desde el último corte">
			<div class="bar-fill" style="width: {progress * 100}%"></div>
		</div>
		<div class="row small">
			<span>GDD {gdd.toFixed(0)} / {GDD_PER_CUT} para el próximo corte</span>
			<span>Corte nº {twin?.cut_number ?? '--'}</span>
		</div>
		<div class="row small">
			<span>Lluvia desde el corte: {Math.round(twin?.prec_accumulated ?? 0)} mm</span>
			<span>Edad: {Number(twin?.stand_age_years ?? 0).toFixed(1)} años</span>
		</div>
	</div>
</div>

<style>
	.wrap {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}
	.picture {
		position: relative;
		line-height: 0;
	}
	img {
		width: 100%;
		height: auto;
		border-radius: 6px;
	}
	.marker {
		position: absolute;
		top: 0;
		bottom: 0;
		box-sizing: border-box;
		border: 3px solid #fff;
		border-radius: 4px;
		box-shadow:
			0 0 0 2px rgba(20, 60, 25, 0.75),
			0 0 14px rgba(255, 255, 255, 0.8);
		transition: left 0.4s;
		pointer-events: none;
	}
	.labels {
		position: relative;
		height: 1.1rem;
		font-size: 0.7rem;
		opacity: 0.75;
	}
	.labels span {
		position: absolute;
		text-align: center;
		white-space: nowrap;
	}
	.labels span.on {
		font-weight: 700;
		opacity: 1;
	}
	.row {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
	}
	.small {
		font-size: 0.85rem;
		opacity: 0.8;
	}
	.bar {
		height: 10px;
		border-radius: 5px;
		background: #d9e2cf;
		overflow: hidden;
		margin: 0.25rem 0;
	}
	.bar-fill {
		height: 100%;
		background: linear-gradient(90deg, #b5c76a, #2f7d3a);
		transition: width 0.4s;
	}
</style>
