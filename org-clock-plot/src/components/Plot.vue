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
                    .tooltipContent((d, node) => `Time: <i>` + node.value.toFixed(2) + `</i> h<br/>Parent: <i>${node.data.relParent}%</i><br/>Total: <i>${node.data.relTot}%</i><br/>`)
                    .transitionDuration(400)
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
    <div ref="plotbox"/>
    
  </div>
</template>

<style scoped>
</style>
