<script >
import icicle from 'icicle-chart';
import * as d3 from 'd3';
import axios from 'axios';

  export default {

  data(){
      return {"plot_data" : {}}
  },
  
  mounted(){

      axios.get("http://127.0.0.1:5000/data").then(
          response => {
              console.log(response.data);


              const color = d3.scaleOrdinal(d3.schemePaired);
              this.plot_data = response.data;
              const myChart = icicle()
                    .label('name')
                    .size('value')
                    .excludeRoot(true)
                    .orientation('lr')
              .sort((a, b) => b.value - a.value)
                    .color((d, parent) => color(parent ? parent.data.name : null))
                    .data(this.plot_data)
              (this.$refs.plotbox);
  
          }
      );
      
  }
  }
  
</script>

<template>
  <div class="plot">
    <h3>Plotting this and that</h3>
    <div ref="plotbox"/>
    
  </div>
</template>

<style scoped>
h1 {
  font-weight: 500;
  font-size: 2.6rem;
  top: -10px;
}

h3 {
  font-size: 1.2rem;
}

.greetings h1,
.greetings h3 {
  text-align: center;
}

@media (min-width: 1024px) {
  .greetings h1,
  .greetings h3 {
    text-align: left;
  }
}
</style>
