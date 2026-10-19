<section>
	<div class="container-xs has-bottom-divider">
		<div class="hero-inner section-inner">
			<h1 class="mt-0 mb-16 reveal-from-bottom">
				<span class="text-color-primary">GE</span>melo{' '}
				<span class="text-color-primary">D</span>igital de Cultivos de{' '}
				<span class="text-color-primary">Alfalfa</span>
				<span class="text-color-primary" style="display:block;">GEDEFEC</span>
			</h1>
			<div class="container-xs">
				<p
					class="mb-32 pb-16 mt-16 reveal-from-bottom"
					style="font-size: 27px;"
					data-reveal-delay="100"
				>
					Propuesta de <strong>gemelo digital</strong> para un tipo concreto de explotación agraria:
					el cultivo de alfalfa, un forraje perenne que se siega varias veces por campaña.
				</p>
			</div>
			<div class="reveal-from-bottom" data-reveal-value="20px" data-reveal-delay="200">
				<img
					loading="lazy"
					src={'/hero-image-initial.jpg'}
					alt="Vista aérea de parcelas de alfalfa en distintos estados de crecimiento"
				/>
			</div>
			<p class="mt-32 pt-32 text-sm fw-700">
				Cada parcela de alfalfa tiene su gemelo digital: integra la meteorología, el histórico de
				cortes y los datos de sensores, simula el rebrote y la cosecha de cada corte y avisa a las
				parcelas vecinas cuando detecta un evento.
			</p>
			<p>
				Los gemelos digitales permiten la digitalización de la realidad física como elemento de base
				para poder aplicar técnicas de inteligencia artificial a grandes volúmenes de datos. Sin
				embargo, el concepto de gemelo digital en agricultura está muy poco consolidado debido,
				especialmente, a la gran complejidad de discretizar una realidad basada en “elementos” vivos
				(una planta o un animal o un conjunto de ellos…) y con unos ámbitos temporales (plantas con
				periodos de vida de un año frente a cultivos plurianuales como la alfalfa, que rebrota tras
				cada corte durante varios años …) y espaciales (pequeña explotaciones frente a otras de mayor
				tamaño), tan heterogéneos y complejos.
			</p>
		</div>
	</div>
</section>

<style lang="scss">
	section {
		text-align: center;
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		margin-top: 1rem;
		padding: 0 1rem;
		background: url('illustration-section-01.svg') no-repeat;
		background-position: right top;
	}

	.section-inner {
		padding-top: 2rem;
		padding-bottom: 2rem;
	}

	.hero-inner {
		// Affects only hero full
		> .hero-content + .hero-figure,
		> .hero-figure + .hero-content {
			margin-top: 2rem;
		}
	}

	.hero-inner {
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
	}

	img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		// Add shadows to create the "card" effect
		box-shadow: color-bg(shadow);
		border-radius: 7px;
	}
</style>
